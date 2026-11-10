import logging

log = logging.getLogger(__name__)
LIMITE_PADRAO = 20


def listar(conexao, categoria, limite=LIMITE_PADRAO):
    log.debug("listando categoria %s", categoria)
    return conexao.execute("SELECT * FROM pecas WHERE categoria = ? LIMIT ?", (categoria, limite)).fetchall()


def remover_duplicadas(pecas, vistos=None):
    vistos = set() if vistos is None else vistos
    unicas = []
    for peca in pecas:
        if peca["id"] not in vistos:
            vistos.add(peca["id"])
            unicas.append(peca)
    return unicas
