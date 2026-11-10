def processarPedido(cliente, itens, cupom, endereco, pagamento, observacao):
    total = 0
    for item in itens:
        if item["qtd"] <= 0:
            continue
        total += item["preco"] * item["qtd"]
    if cupom == "PRIMEIRA":
        total *= 0.9
    elif cupom == "FIDELIDADE" and cliente["pedidos"] > 5:
        total *= 0.85
    if endereco["uf"] in ("AM", "RR", "AP"):
        total += 40
    elif endereco["uf"] == "PR":
        total += 10
    if pagamento == "boleto" or pagamento == "pix":
        total *= 0.97
    if observacao and len(observacao) > 200:
        observacao = observacao[:200]
    return {"total": round(total, 2), "obs": observacao}
