"""Microsserviço HTTP do Agente Arquiteto: POST /webhook recebe eventos de Pull Request."""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agents.arquiteto.agente import ArquitetoController, EstrategiaOrientacao, PayloadInvalido


def criar_servidor(porta: int = 8081, estrategia=None) -> ThreadingHTTPServer:
    controller = ArquitetoController(estrategia)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _responder(self, codigo, corpo):
            dados = json.dumps(corpo, ensure_ascii=False).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_POST(self):
            if self.path != "/webhook":
                return self._responder(404, {"erro": "rota inexistente"})
            try:
                evento = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"null")
                self._responder(200, controller.receber_evento(evento))
            except (json.JSONDecodeError, PayloadInvalido) as erro:
                self._responder(400, {"erro": str(erro)})

    return ThreadingHTTPServer(("127.0.0.1", porta), Handler)


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    estrategia = EstrategiaOrientacao() if "--orientacao" in sys.argv else None
    print(f"Agente Arquiteto ouvindo em http://127.0.0.1:{porta}/webhook")
    criar_servidor(porta, estrategia).serve_forever()
