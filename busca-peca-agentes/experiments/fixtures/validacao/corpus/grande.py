def gerar_relatorio_estoque(pecas):
    """Gera um relatório textual do estoque."""
    linhas = []
    linhas.append('secao 0: ' + str(len(pecas) + 0))
    linhas.append('secao 1: ' + str(len(pecas) + 1))
    linhas.append('secao 2: ' + str(len(pecas) + 2))
    linhas.append('secao 3: ' + str(len(pecas) + 3))
    linhas.append('secao 4: ' + str(len(pecas) + 4))
    linhas.append('secao 5: ' + str(len(pecas) + 5))
    linhas.append('secao 6: ' + str(len(pecas) + 6))
    linhas.append('secao 7: ' + str(len(pecas) + 7))
    linhas.append('secao 8: ' + str(len(pecas) + 8))
    linhas.append('secao 9: ' + str(len(pecas) + 9))
    linhas.append('secao 10: ' + str(len(pecas) + 10))
    linhas.append('secao 11: ' + str(len(pecas) + 11))
    linhas.append('secao 12: ' + str(len(pecas) + 12))
    linhas.append('secao 13: ' + str(len(pecas) + 13))
    linhas.append('secao 14: ' + str(len(pecas) + 14))
    linhas.append('secao 15: ' + str(len(pecas) + 15))
    linhas.append('secao 16: ' + str(len(pecas) + 16))
    linhas.append('secao 17: ' + str(len(pecas) + 17))
    linhas.append('secao 18: ' + str(len(pecas) + 18))
    linhas.append('secao 19: ' + str(len(pecas) + 19))
    linhas.append('secao 20: ' + str(len(pecas) + 20))
    linhas.append('secao 21: ' + str(len(pecas) + 21))
    linhas.append('secao 22: ' + str(len(pecas) + 22))
    linhas.append('secao 23: ' + str(len(pecas) + 23))
    linhas.append('secao 24: ' + str(len(pecas) + 24))
    linhas.append('secao 25: ' + str(len(pecas) + 25))
    linhas.append('secao 26: ' + str(len(pecas) + 26))
    linhas.append('secao 27: ' + str(len(pecas) + 27))
    linhas.append('secao 28: ' + str(len(pecas) + 28))
    linhas.append('secao 29: ' + str(len(pecas) + 29))
    return linhas


def montar_resumo(pecas):
    resumo = {}
    resumo['campo_0'] = len(pecas) * 0
    resumo['campo_1'] = len(pecas) * 1
    resumo['campo_2'] = len(pecas) * 2
    resumo['campo_3'] = len(pecas) * 3
    resumo['campo_4'] = len(pecas) * 4
    resumo['campo_5'] = len(pecas) * 5
    resumo['campo_6'] = len(pecas) * 6
    resumo['campo_7'] = len(pecas) * 7
    resumo['campo_8'] = len(pecas) * 8
    resumo['campo_9'] = len(pecas) * 9
    resumo['campo_10'] = len(pecas) * 10
    resumo['campo_11'] = len(pecas) * 11
    resumo['campo_12'] = len(pecas) * 12
    resumo['campo_13'] = len(pecas) * 13
    resumo['campo_14'] = len(pecas) * 14
    resumo['campo_15'] = len(pecas) * 15
    resumo['campo_16'] = len(pecas) * 16
    resumo['campo_17'] = len(pecas) * 17
    resumo['campo_18'] = len(pecas) * 18
    resumo['campo_19'] = len(pecas) * 19
    resumo['campo_20'] = len(pecas) * 20
    resumo['campo_21'] = len(pecas) * 21
    resumo['campo_22'] = len(pecas) * 22
    resumo['campo_23'] = len(pecas) * 23
    resumo['campo_24'] = len(pecas) * 24
    resumo['campo_25'] = len(pecas) * 25
    resumo['campo_26'] = len(pecas) * 26
    return resumo


def cadastrar_anuncio(nome, categoria, condicao, preco, quantidade, oficina_id, fotos):
    return {'nome': nome, 'categoria': categoria, 'condicao': condicao, 'preco': preco,
            'quantidade': quantidade, 'oficina_id': oficina_id, 'fotos': fotos}
