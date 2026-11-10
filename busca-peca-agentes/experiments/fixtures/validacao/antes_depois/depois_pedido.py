DESCONTOS_CUPOM = {"PRIMEIRA": 0.9}
FRETE_POR_UF = {"AM": 40, "RR": 40, "AP": 40, "PR": 10}
DESCONTO_PAGAMENTO_A_VISTA = 0.97
LIMITE_OBSERVACAO = 200


def subtotal_itens(itens):
    return sum(item["preco"] * item["qtd"] for item in itens if item["qtd"] > 0)


def fator_cupom(cupom, cliente):
    if cupom == "FIDELIDADE" and cliente["pedidos"] > 5:
        return 0.85
    return DESCONTOS_CUPOM.get(cupom, 1.0)


def fator_pagamento(pagamento):
    return DESCONTO_PAGAMENTO_A_VISTA if pagamento in ("boleto", "pix") else 1.0


def processar_pedido(pedido):
    total = subtotal_itens(pedido["itens"]) * fator_cupom(pedido["cupom"], pedido["cliente"])
    total += FRETE_POR_UF.get(pedido["endereco"]["uf"], 0)
    total *= fator_pagamento(pedido["pagamento"])
    observacao = pedido.get("observacao")
    observacao = observacao[:LIMITE_OBSERVACAO] if observacao else observacao
    return {"total": round(total, 2), "obs": observacao}
