"""Funções de catálogo escritas seguindo Clean Code."""
TAXA_PLATAFORMA = 0.08


class CatalogoPecas:
    def __init__(self, pecas):
        self.pecas = list(pecas)

    def disponiveis(self):
        return [peca for peca in self.pecas if peca["quantidade"] > 0]

    def por_categoria(self, categoria):
        return [peca for peca in self.disponiveis() if peca["categoria"] == categoria]


def valor_liquido_vendedor(preco_venda):
    return round(preco_venda * (1 - TAXA_PLATAFORMA), 2)


def formatar_preco(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
