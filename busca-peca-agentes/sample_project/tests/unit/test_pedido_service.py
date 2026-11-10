import unittest

from buscapeca.models import ItemPedido, Pedido
from buscapeca.repositories.conexao import criar_conexao
from buscapeca.repositories.peca_repository import PecaRepository
from buscapeca.repositories.pedido_repository import PedidoRepository
from buscapeca.services.pedido_service import PedidoService


class TestCalculoPedido(unittest.TestCase):
    def setUp(self):
        conexao = criar_conexao()
        self.servico = PedidoService(PecaRepository(conexao), PedidoRepository(conexao))

    def test_total_com_frete(self):
        pedido = Pedido(1, [ItemPedido(1, 2, 50.0)])
        self.assertEqual(self.servico.calcular_total(pedido), 115.0)

    def test_total_frete_gratis(self):
        pedido = Pedido(1, [ItemPedido(1, 3, 100.0)])
        self.assertEqual(self.servico.calcular_total(pedido), 300.0)

    def test_subtotal_item(self):
        self.assertEqual(ItemPedido(1, 3, 19.99).subtotal(), 59.97)

    def test_pedido_vazio_cobra_frete(self):
        self.assertEqual(self.servico.calcular_total(Pedido(1)), 15.0)
