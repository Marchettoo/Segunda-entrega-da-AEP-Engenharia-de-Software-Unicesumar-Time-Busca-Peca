from buscapeca.models import Peca
from buscapeca.services.peca_service import PecaInvalidaError, PecaService


class PecaController:
    def __init__(self, servico: PecaService):
        self.servico = servico

    def post_peca(self, corpo: dict) -> dict:
        try:
            peca = self.servico.cadastrar_peca(Peca(**corpo))
            return {"status": 201, "id": peca.id}
        except (PecaInvalidaError, TypeError) as erro:
            return {"status": 400, "erro": str(erro)}

    def get_pecas(self, categoria: str) -> dict:
        pecas = self.servico.buscar_disponiveis(categoria)
        return {"status": 200, "itens": [p.__dict__ for p in pecas]}
