import unittest


def calcularTotal(itens):
    return sum(item.preco for item in itens)


class item_pedido:
    def __init__(self, peca, quantidade):
        self.peca = peca
        self.quantidade = quantidade


def aplicar_desconto(valor):
    x = valor * 0.9
    return round(x, 2)


def listar_nomes(pecas):
    return [p.nome for p in pecas]


class TestNomes(unittest.TestCase):
    def setUp(self):
        self.valor = 10

    def test_desconto(self):
        self.assertEqual(aplicar_desconto(10), 9.0)
