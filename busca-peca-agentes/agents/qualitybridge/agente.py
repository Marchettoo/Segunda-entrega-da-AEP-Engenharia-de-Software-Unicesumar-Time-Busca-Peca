"""QualityBridge — agente de testes em camadas: entrada -> execução -> processamento -> relatório."""
import argparse
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml
from jinja2 import Template

COLETOR = Path(__file__).with_name("_coletor_unittest.py")


# ---------------- Camada de entrada (configuração validada) ----------------
class ConfiguracaoInvalida(Exception):
    pass


@dataclass
class Suite:
    nome: str
    executor: str
    caminho: str
    padrao: str = "test_*.py"
    rapida: bool = False


@dataclass
class Configuracao:
    projeto: str
    raiz: Path
    suites: list
    saida: Path
    banco: Path


def carregar_configuracao(arquivo) -> Configuracao:
    arquivo = Path(arquivo)
    try:
        dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as e:
        raise ConfiguracaoInvalida(f"não foi possível ler {arquivo.name}: {e.__class__.__name__}")
    if not isinstance(dados, dict) or not isinstance(dados.get("suites"), list) or not dados["suites"]:
        raise ConfiguracaoInvalida("o YAML deve conter a chave 'suites' com ao menos uma suíte")
    base = arquivo.parent
    suites = []
    for s in dados["suites"]:
        faltando = {"nome", "executor", "caminho"} - set(s)
        if faltando:
            raise ConfiguracaoInvalida(f"suíte sem campos obrigatórios: {sorted(faltando)}")
        suites.append(Suite(**{k: s[k] for k in ("nome", "executor", "caminho", "padrao", "rapida") if k in s}))
    return Configuracao(dados.get("projeto", "projeto"), (base / dados.get("raiz", ".")).resolve(), suites,
                        (base / dados.get("saida", "qb_relatorios")).resolve(),
                        (base / dados.get("banco", "qualitybridge.db")).resolve())


# ---------------- Modelo de resultados ----------------
@dataclass
class ResultadoTeste:
    suite: str
    nome: str
    status: str
    tempo_s: float
    mensagem: str = ""


@dataclass
class ResultadoSuite:
    suite: str
    executor: str
    situacao: str  # executada | indisponivel
    testes: list = field(default_factory=list)
    duracao_s: float = 0.0
    observacao: str = ""


# ---------------- Adapter (GoF estrutural) ----------------
class AdaptadorUnittest:
    """Converte a saída JSON do coletor unittest no modelo comum do agente."""

    @staticmethod
    def converter(suite: str, saida_json: str) -> list:
        return [ResultadoTeste(suite, r["id"], r["status"], r["tempo_s"], r["mensagem"]) for r in json.loads(saida_json)]


class AdaptadorJUnitXML:
    """Converte JUnit XML (formato do pytest/Playwright) no modelo comum do agente."""

    @staticmethod
    def converter(suite: str, xml: str) -> list:
        resultados = []
        for caso in ET.fromstring(xml).iter("testcase"):
            status = "falhou" if caso.find("failure") is not None else "erro" if caso.find("error") is not None \
                else "ignorado" if caso.find("skipped") is not None else "passou"
            resultados.append(ResultadoTeste(suite, f"{caso.get('classname')}.{caso.get('name')}", status,
                                             float(caso.get("time", 0))))
        return resultados


# ---------------- Factory Method (GoF criação) ----------------
class Executor(ABC):
    @abstractmethod
    def disponivel(self) -> bool: ...

    @abstractmethod
    def executar(self, suite: Suite, raiz: Path) -> list: ...

    def rodar(self, suite: Suite, raiz: Path) -> ResultadoSuite:
        if not self.disponivel():
            return ResultadoSuite(suite.nome, suite.executor, "indisponivel",
                                  observacao=f"ferramenta '{suite.executor}' não instalada no ambiente")
        inicio = time.perf_counter()
        testes = self.executar(suite, raiz)
        return ResultadoSuite(suite.nome, suite.executor, "executada", testes, time.perf_counter() - inicio)


class ExecutorUnittest(Executor):
    def disponivel(self):
        return True

    def executar(self, suite, raiz):
        proc = subprocess.run([sys.executable, str(COLETOR), str(raiz), str(raiz / suite.caminho), suite.padrao],
                              cwd=raiz, capture_output=True, text=True, timeout=600)
        return AdaptadorUnittest.converter(suite.nome, proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "[]")


class ExecutorPytest(Executor):
    def disponivel(self):
        return importlib.util.find_spec("pytest") is not None

    def executar(self, suite, raiz):
        xml = raiz / ".qb_pytest.xml"
        subprocess.run([sys.executable, "-m", "pytest", suite.caminho, f"--junitxml={xml}", "-q"], cwd=raiz,
                       capture_output=True, timeout=600)
        return AdaptadorJUnitXML.converter(suite.nome, xml.read_text())


class ExecutorPlaywright(Executor):
    def disponivel(self):
        return shutil.which("npx") is not None and (Path.cwd() / "node_modules" / "@playwright").exists()

    def executar(self, suite, raiz):
        proc = subprocess.run(["npx", "playwright", "test", suite.caminho, "--reporter=junit"], cwd=raiz,
                              capture_output=True, text=True, timeout=900)
        return AdaptadorJUnitXML.converter(suite.nome, proc.stdout)


class FabricaExecutores:
    registro = {"unittest": ExecutorUnittest, "pytest": ExecutorPytest, "playwright": ExecutorPlaywright}

    @classmethod
    def criar(cls, tipo: str) -> Executor:
        if tipo not in cls.registro:
            raise ConfiguracaoInvalida(f"executor desconhecido: {tipo}")
        return cls.registro[tipo]()


# ---------------- Strategy (GoF comportamental) ----------------
class EstrategiaExecucao(ABC):
    nome = ""

    @abstractmethod
    def selecionar(self, suites: list) -> list: ...


class EstrategiaCompleta(EstrategiaExecucao):
    nome = "completa"

    def selecionar(self, suites):
        return suites


class EstrategiaRapida(EstrategiaExecucao):
    nome = "rapida"

    def selecionar(self, suites):
        return [s for s in suites if s.rapida]


ESTRATEGIAS = {"completa": EstrategiaCompleta, "rapida": EstrategiaRapida}

# ---------------- Camada de relatório ----------------
MODELO_HTML = Template("""<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><title>QualityBridge — {{ r.projeto }}</title>
<style>body{font-family:Arial,sans-serif;margin:24px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}
.passou{color:#1a7f37}.falhou,.erro{color:#cf222e}.indisponivel,.ignorado{color:#9a6700}</style></head><body>
<h1>QualityBridge — {{ r.projeto }}</h1>
<p>Execução {{ r.id_execucao }} · estratégia <b>{{ r.estrategia }}</b> · status <b id="status">{{ r.status }}</b></p>
<p>Total: <b id="total">{{ r.totais.total }}</b> · Passaram: <b id="passou">{{ r.totais.passou }}</b> ·
Falharam: <b id="falhou">{{ r.totais.falhou }}</b> · Erros: <b id="erro">{{ r.totais.erro }}</b> · Duração: {{ '%.2f'|format(r.duracao_s) }} s</p>
{% for s in r.suites %}<h2>Suíte {{ s.suite }} ({{ s.executor }}) — <span class="{{ s.situacao }}">{{ s.situacao }}</span></h2>
{% if s.observacao %}<p>{{ s.observacao }}</p>{% endif %}
{% if s.testes %}<table><tr><th>Teste</th><th>Status</th><th>Tempo (s)</th><th>Mensagem</th></tr>
{% for t in s.testes %}<tr><td>{{ t.nome }}</td><td class="{{ t.status }}">{{ t.status }}</td><td>{{ '%.4f'|format(t.tempo_s) }}</td><td>{{ t.mensagem }}</td></tr>{% endfor %}
</table>{% endif %}{% endfor %}</body></html>""")


def gerar_junit(execucao: dict) -> str:
    raiz = ET.Element("testsuites", tests=str(execucao["totais"]["total"]), failures=str(execucao["totais"]["falhou"]),
                      errors=str(execucao["totais"]["erro"]))
    for s in execucao["suites"]:
        el = ET.SubElement(raiz, "testsuite", name=s["suite"], tests=str(len(s["testes"])))
        for t in s["testes"]:
            caso = ET.SubElement(el, "testcase", name=t["nome"], time=f"{t['tempo_s']:.4f}")
            if t["status"] in ("falhou", "erro"):
                ET.SubElement(caso, "failure" if t["status"] == "falhou" else "error", message=t["mensagem"])
    return ET.tostring(raiz, encoding="unicode")


class Historico:
    def __init__(self, banco: Path):
        self.con = sqlite3.connect(banco)
        self.con.execute("CREATE TABLE IF NOT EXISTS execucoes (id TEXT PRIMARY KEY, data TEXT, estrategia TEXT,"
                         " status TEXT, total INTEGER, passou INTEGER, falhou INTEGER, erro INTEGER, duracao_s REAL)")

    def registrar(self, e: dict):
        t = e["totais"]
        self.con.execute("INSERT INTO execucoes VALUES (?,?,?,?,?,?,?,?,?)", (e["id_execucao"], e["data"], e["estrategia"],
                         e["status"], t["total"], t["passou"], t["falhou"], t["erro"], e["duracao_s"]))
        self.con.commit()

    def contar(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM execucoes").fetchone()[0]


# ---------------- Controller (GRASP) ----------------
class QualityBridge:
    def __init__(self, config: Configuracao, estrategia: str = "completa"):
        self.config, self.estrategia = config, ESTRATEGIAS[estrategia]()

    def executar(self) -> dict:
        inicio = time.perf_counter()
        resultados = [FabricaExecutores.criar(s.executor).rodar(s, self.config.raiz)
                      for s in self.estrategia.selecionar(self.config.suites)]
        testes = [t for r in resultados for t in r.testes]
        totais = {k: sum(1 for t in testes if t.status == k) for k in ("passou", "falhou", "erro", "ignorado")}
        totais["total"] = len(testes)
        execucao = {"projeto": self.config.projeto, "id_execucao": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                    "data": datetime.now().isoformat(timespec="seconds"), "estrategia": self.estrategia.nome,
                    "status": "FALHOU" if totais["falhou"] or totais["erro"] else "PASSOU", "totais": totais,
                    "suites": [asdict(r) for r in resultados], "duracao_s": time.perf_counter() - inicio}
        self.publicar(execucao)
        return execucao

    def publicar(self, e: dict):
        self.config.saida.mkdir(parents=True, exist_ok=True)
        (self.config.saida / "relatorio.html").write_text(MODELO_HTML.render(r=e), encoding="utf-8")
        (self.config.saida / "relatorio.json").write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.config.saida / "junit.xml").write_text(gerar_junit(e), encoding="utf-8")
        Historico(self.config.banco).registrar(e)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="qualitybridge", description="Agente de Testes QualityBridge")
    sub = ap.add_subparsers(dest="comando", required=True)
    run = sub.add_parser("run"); run.add_argument("--config", default="qualitybridge.yaml")
    run.add_argument("--estrategia", choices=list(ESTRATEGIAS), default="completa")
    hist = sub.add_parser("historico"); hist.add_argument("--config", default="qualitybridge.yaml")
    a = ap.parse_args(argv)
    try:
        config = carregar_configuracao(a.config)
    except ConfiguracaoInvalida as e:
        print(f"[QualityBridge] configuração inválida: {e}", file=sys.stderr)
        return 2
    if a.comando == "historico":
        print(f"{Historico(config.banco).contar()} execuções registradas em {config.banco.name}")
        return 0
    e = QualityBridge(config, a.estrategia).executar()
    t = e["totais"]
    for s in e["suites"]:
        print(f"  suíte {s['suite']:<12} [{s['executor']}] {s['situacao']:<12} {len(s['testes'])} testes {s['observacao']}")
    print(f"[QualityBridge] {e['status']} — total {t['total']} | passou {t['passou']} | falhou {t['falhou']} | "
          f"erro {t['erro']} | {e['duracao_s']:.2f}s | relatórios em {config.saida.name}/")
    return 0 if e["status"] == "PASSOU" else 1


if __name__ == "__main__":
    sys.exit(main())
