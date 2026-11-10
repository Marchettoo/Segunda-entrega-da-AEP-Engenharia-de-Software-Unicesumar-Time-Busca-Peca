import unittest

from buscapeca.models import Peca
from buscapeca.repositories.conexao import criar_conexao
from buscapeca.repositories.peca_repository import PecaRepository
from buscapeca.services.peca_service import PecaInvalidaError, PecaService


def nova_peca(**extra):
    dados = dict(nome="Alternador", categoria="eletrica", condicao="usada", preco=250.0, quantidade=2, oficina_id=1)
    dados.update(extra)
    return Peca(**dados)


class TestPecaService(unittest.TestCase):
    def setUp(self):
        self.servico = PecaService(PecaRepository(criar_conexao()))

    def test_cadastra_peca_valida(self):
        self.assertIsNotNone(self.servico.cadastrar_peca(nova_peca()).id)

    def test_rejeita_nome_vazio(self):
        with self.assertRaises(PecaInvalidaError):
            self.servico.cadastrar_peca(nova_peca(nome="  "))

    def test_rejeita_condicao_invalida(self):
        with self.assertRaises(PecaInvalidaError):
            self.servico.cadastrar_peca(nova_peca(condicao="quebrada"))

    def test_rejeita_preco_zero(self):
        with self.assertRaises(PecaInvalidaError):
            self.servico.cadastrar_peca(nova_peca(preco=0))

    def test_preco_sugerido_usada(self):
        self.assertEqual(self.servico.preco_sugerido(100.0, "usada"), 60.0)

    def test_preco_sugerido_excedente(self):
        self.assertEqual(self.servico.preco_sugerido(100.0, "excedente"), 85.0)

    def test_busca_ignora_sem_estoque(self):
        self.servico.cadastrar_peca(nova_peca())
        self.servico.cadastrar_peca(nova_peca(nome="Motor de partida", quantidade=0))
        self.assertEqual(len(self.servico.buscar_disponiveis("eletrica")), 1)

    def test_pecas_reaproveitaveis(self):
        self.servico.cadastrar_peca(nova_peca(condicao="excedente"))
        self.servico.cadastrar_peca(nova_peca(condicao="nova"))
        self.assertEqual(len(self.servico.pecas_reaproveitaveis()), 1)
