import sqlite3


def criar_conexao(caminho: str = ":memory:") -> sqlite3.Connection:
    conexao = sqlite3.connect(caminho)
    conexao.execute(
        "CREATE TABLE IF NOT EXISTS pecas (id INTEGER PRIMARY KEY, nome TEXT, categoria TEXT,"
        " condicao TEXT, preco REAL, quantidade INTEGER, oficina_id INTEGER)"
    )
    conexao.execute(
        "CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY, comprador_id INTEGER, status TEXT, total REAL)"
    )
    return conexao
