"""Executado em subprocesso: roda unittest e emite JSON com o resultado de cada teste."""
import json
import sys
import time
import unittest


class Coletor(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.registros, self._t0 = [], 0

    def startTest(self, teste):
        self._t0 = time.perf_counter()
        super().startTest(teste)

    def _reg(self, teste, status, msg=""):
        self.registros.append({"id": teste.id(), "status": status, "tempo_s": time.perf_counter() - self._t0, "mensagem": msg})

    def addSuccess(self, t):
        super().addSuccess(t); self._reg(t, "passou")

    def addFailure(self, t, err):
        super().addFailure(t, err); self._reg(t, "falhou", self._exc_info_to_string(err, t).splitlines()[-1])

    def addError(self, t, err):
        super().addError(t, err); self._reg(t, "erro", self._exc_info_to_string(err, t).splitlines()[-1])

    def addSkip(self, t, motivo):
        super().addSkip(t, motivo); self._reg(t, "ignorado", motivo)


if __name__ == "__main__":
    inicio, caminho, padrao = sys.argv[1], sys.argv[2], sys.argv[3]
    suite = unittest.defaultTestLoader.discover(caminho, pattern=padrao, top_level_dir=inicio)
    with open("/dev/null", "w") as nulo:
        resultado = unittest.TextTestRunner(stream=nulo, resultclass=Coletor, verbosity=0).run(suite)
    print(json.dumps(resultado.registros))
