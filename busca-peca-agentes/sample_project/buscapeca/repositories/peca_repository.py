"""Persistência de peças em SQLite (consultas sempre parametrizadas)."""
from typing import List, Optional

from buscapeca.models import Peca


class PecaRepository:
    def __init__(self, conexao):
        self.conexao = conexao

    def salvar(self, peca: Peca) -> Peca:
        cursor = self.conexao.execute(
            "INSERT INTO pecas (nome, categoria, condicao, preco, quantidade, oficina_id) VALUES (?, ?, ?, ?, ?, ?)",
            (peca.nome, peca.categoria, peca.condicao, peca.preco, peca.quantidade, peca.oficina_id),
        )
        peca.id = cursor.lastrowid
        return peca

    def buscar_por_id(self, peca_id: int) -> Optional[Peca]:
        linha = self.conexao.execute(
            "SELECT nome, categoria, condicao, preco, quantidade, oficina_id, id FROM pecas WHERE id = ?", (peca_id,)
        ).fetchone()
        return Peca(*linha) if linha else None

    def buscar_por_categoria(self, categoria: str) -> List[Peca]:
        linhas = self.conexao.execute(
            "SELECT nome, categoria, condicao, preco, quantidade, oficina_id, id FROM pecas WHERE categoria = ?",
            (categoria,),
        ).fetchall()
        return [Peca(*linha) for linha in linhas]

    def listar_excedentes(self) -> List[Peca]:
        linhas = self.conexao.execute(
            "SELECT nome, categoria, condicao, preco, quantidade, oficina_id, id FROM pecas WHERE condicao = ?",
            ("excedente",),
        ).fetchall()
        return [Peca(*linha) for linha in linhas]

    def atualizar_quantidade(self, peca_id: int, quantidade: int) -> None:
        self.conexao.execute("UPDATE pecas SET quantidade = ? WHERE id = ?", (quantidade, peca_id))
