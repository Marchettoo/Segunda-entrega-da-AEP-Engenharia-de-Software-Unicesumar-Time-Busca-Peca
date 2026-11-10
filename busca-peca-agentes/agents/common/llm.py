"""Camada de acesso a LLM compartilhada pelos agentes híbridos.

Adapter + Factory Method: os agentes dependem apenas de `LLMProvider`.
- TemplateLLMProvider: provedor determinístico (respostas por modelo de texto),
  usado nos testes controlados da Entrega 2 por reprodutibilidade e porque o
  ambiente de testes não possui acesso de rede.
- OpenAICompatibleProvider: chamada HTTP real a uma API compatível com OpenAI
  (OpenAI, Gemini via endpoint compatível etc.), ativada por variáveis de ambiente.
"""
import json
import os
import urllib.request
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    nome = "abstrato"

    @abstractmethod
    def completar(self, tarefa: str, contexto: dict) -> str:
        ...


MODELOS_TEXTO = {
    "sugestao_refatoracao": "Sugestão: {regra} em `{simbolo}` — {dica}",
    "explicacao_didatica": "Em linguagem simples: {explicacao}",
    "resumo_modulo": "Módulo `{modulo}`: {responsabilidade}",
    "explicacao_achado": "Por que isso importa: {motivo}",
}


class TemplateLLMProvider(LLMProvider):
    nome = "template-deterministico"

    def completar(self, tarefa: str, contexto: dict) -> str:
        modelo = MODELOS_TEXTO.get(tarefa, "{texto}")
        try:
            return modelo.format(**contexto)
        except KeyError:
            return contexto.get("texto", "")


class OpenAICompatibleProvider(LLMProvider):
    nome = "openai-compativel"

    def __init__(self, url: str, chave: str, modelo: str):
        self.url, self.chave, self.modelo = url, chave, modelo

    def completar(self, tarefa: str, contexto: dict) -> str:
        prompt = f"Tarefa: {tarefa}\nContexto (JSON): {json.dumps(contexto, ensure_ascii=False)}\nResponda em português, em até 3 frases."
        corpo = json.dumps({"model": self.modelo, "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(self.url, data=corpo, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.chave}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dados = json.load(resp)
        return dados["choices"][0]["message"]["content"].strip()


def criar_provedor() -> LLMProvider:
    """Factory Method: escolhe o provedor pelo ambiente (padrão: determinístico)."""
    if os.getenv("AEP_LLM_URL") and os.getenv("AEP_LLM_KEY"):
        return OpenAICompatibleProvider(os.environ["AEP_LLM_URL"], os.environ["AEP_LLM_KEY"],
                                        os.getenv("AEP_LLM_MODEL", "gpt-4o-mini"))
    return TemplateLLMProvider()
