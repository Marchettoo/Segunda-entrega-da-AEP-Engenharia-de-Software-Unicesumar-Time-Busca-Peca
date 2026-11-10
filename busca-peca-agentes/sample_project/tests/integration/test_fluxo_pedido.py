import unittest

from buscapeca.controllers.peca_controller import PecaController
from buscapeca.controllers.pedido_controller import PedidoController
from buscapeca.repositories.conexao import criar_conexao
from buscapeca.repositories.peca_repository import PecaRepository
from buscapeca.repositories.pedido_repository import PedidoRepository
from buscapeca.services.peca_service import PecaService
from buscapeca.services.pedido_service import PedidoService

PECA = {"nome": "Radiador", "categoria": "arrefecimento", "condicao": "excedente",
        "preco": 180.0, "quantidade": 3, "oficina_id": 7}


class TestFluxoPedido(unittest.TestCase):
    def setUp(self):
        conexao = criar_conexao()
        pecas = PecaRepository(conexao)
        self.pecas = PecaController(PecaService(pecas))
        self.pedidos = PedidoController(PedidoService(pecas, PedidoRepository(conexao)))

    def test_anunciar_e_listar(self):
        self.assertEqual(self.pecas.post_peca(dict(PECA))["status"], 201)
        self.assertEqual(len(self.pecas.get_pecas("arrefecimento")["itens"]), 1)

    def test_anuncio_invalido_retorna_400(self):
        self.assertEqual(self.pecas.post_peca({"nome": "x"})["status"], 400)

    def test_compra_baixa_estoque(self):
        peca_id = self.pecas.post_peca(dict(PECA))["id"]
        resposta = self.pedidos.post_pedido({"comprador_id": 2, "itens": [{"peca_id": peca_id, "quantidade": 2}]})
        self.assertEqual(resposta["status"], 201)
        self.assertEqual(self.pecas.get_pecas("arrefecimento")["itens"][0]["quantidade"], 1)

    def test_compra_sem_estoque_retorna_409(self):
        peca_id = self.pecas.post_peca(dict(PECA))["id"]
        resposta = self.pedidos.post_pedido({"comprador_id": 2, "itens": [{"peca_id": peca_id, "quantidade": 9}]})
        self.assertEqual(resposta["status"], 409)

    def test_peca_inexistente_retorna_409(self):
        resposta = self.pedidos.post_pedido({"comprador_id": 2, "itens": [{"peca_id": 999, "quantidade": 1}]})
        self.assertEqual(resposta["status"], 409)
