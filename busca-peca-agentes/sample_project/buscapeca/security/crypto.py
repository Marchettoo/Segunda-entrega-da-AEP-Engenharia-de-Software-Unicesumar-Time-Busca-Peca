"""Camada de segurança: derivação e verificação de senhas."""
import hashlib
import hmac
import os

ITERACOES = 120_000


def hash_senha(senha: str, sal: bytes = None) -> str:
    sal = sal or os.urandom(16)
    derivada = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, ITERACOES)
    return sal.hex() + ":" + derivada.hex()


def verificar_senha(senha: str, armazenado: str) -> bool:
    sal_hex, derivada_hex = armazenado.split(":")
    calculada = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal_hex), ITERACOES)
    return hmac.compare_digest(calculada.hex(), derivada_hex)
