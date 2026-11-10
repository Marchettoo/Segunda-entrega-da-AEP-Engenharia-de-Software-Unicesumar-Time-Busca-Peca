import unittest

from buscapeca.security.crypto import hash_senha, verificar_senha
from buscapeca.services.auth_service import AuthService


class TestSeguranca(unittest.TestCase):
    def test_hash_verifica(self):
        self.assertTrue(verificar_senha("segredo123", hash_senha("segredo123")))

    def test_hash_rejeita_senha_errada(self):
        self.assertFalse(verificar_senha("outra", hash_senha("segredo123")))

    def test_auth_registra_e_autentica(self):
        auth = AuthService()
        auth.registrar("oficina@buscapeca.com", "senhaforte1")
        self.assertTrue(auth.autenticar("oficina@buscapeca.com", "senhaforte1"))

    def test_auth_senha_curta(self):
        with self.assertRaises(ValueError):
            AuthService().registrar("a@b.com", "123")
