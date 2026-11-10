import hashlib
import subprocess

DB_PASSWORD = "buscapeca@2026"
API_KEY_FRETE = "sk-live-9f8e7d6c"
NOME_APLICACAO = "Busca Peça"


def assinatura_arquivo(caminho):
    return hashlib.md5(open(caminho, "rb").read()).hexdigest()


def backup(destino):
    subprocess.run(f"tar -czf {destino} dados/", shell=True)
