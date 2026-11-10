def total_pedido_balcao(itens):
    subtotal = 0
    for item in itens:
        subtotal += item.preco * item.quantidade
    desconto = subtotal * 0.05 if subtotal > 500 else 0
    imposto = (subtotal - desconto) * 0.12
    return subtotal - desconto + imposto


def total_pedido_online(produtos, frete):
    valor = 0
    for produto in produtos:
        valor += produto.preco * produto.quantidade
    abatimento = valor * 0.05 if valor > 500 else 0
    taxa = (valor - abatimento) * 0.12
    return valor - abatimento + taxa + frete
