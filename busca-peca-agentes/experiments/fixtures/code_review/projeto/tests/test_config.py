import unittest

SENHA_TESTE = "senha-de-teste-123"


class TestConfig(unittest.TestCase):
    def test_senha(self):
        self.assertTrue(len(SENHA_TESTE) > 8)
