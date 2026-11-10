import logging

log = logging.getLogger(__name__)


def adicionar_item(item, carrinho=[]):
    carrinho.append(item)
    return carrinho


def total(carrinho):
    try:
        return sum(i["preco"] for i in carrinho)
    except:
        return 0


def cancelar(pedido):
    if pedido.get("pago") == None:
        pedido["status"] = "cancelado"
    return pedido


def aplicar_regra(expressao, contexto):
    return eval(expressao, {}, contexto)


def notificar(pedido):
    try:
        log.info("pedido %s notificado", pedido["id"])
    except KeyError:
        pass
    print("notificado", pedido)


def calcular_frete(cep, tabela={}):  # nosec - cache somente leitura, revisado
    return tabela.get(cep[:5], 15.0)
