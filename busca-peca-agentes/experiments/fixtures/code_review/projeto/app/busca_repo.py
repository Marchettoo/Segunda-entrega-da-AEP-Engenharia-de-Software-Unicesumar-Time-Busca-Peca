import sqlite3

TABELA = "pecas"


def buscar_por_nome(conexao, nome):
    return conexao.execute(f"SELECT * FROM pecas WHERE nome = '{nome}'").fetchall()


def buscar_por_oficina(conexao, oficina_id):
    return conexao.execute("SELECT * FROM pecas WHERE oficina_id = " + str(oficina_id)).fetchall()


def contar_pecas(conexao):
    return conexao.execute(f"SELECT COUNT(*) FROM {TABELA}").fetchone()[0]


def buscar_seguro(conexao, nome):
    return conexao.execute("SELECT * FROM pecas WHERE nome = ?", (nome,)).fetchall()
