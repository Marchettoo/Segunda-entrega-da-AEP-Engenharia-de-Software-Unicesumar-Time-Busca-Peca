"""Gera os gráficos da Entrega 2 a partir de results/casos.csv, amostras_tempo.csv e metricas.json."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RES = Path(__file__).resolve().parents[1] / "results"
OUT = RES / "graficos"; OUT.mkdir(exist_ok=True)
AZUL, AZUL2, CINZA, VERDE, VERMELHO, LARANJA = "#1F3864", "#4A6FA5", "#A6A6A6", "#2E8B57", "#C0392B", "#D68910"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
casos = pd.read_csv(RES / "casos.csv", sep=";")
amostras = pd.read_csv(RES / "amostras_tempo.csv", sep=";")
m = json.load(open(RES / "metricas.json", encoding="utf-8"))
AGENTES = ["Documentação", "Validação de Código", "Arquiteto", "Code Review", "Testes (QualityBridge)"]
CURTO = {"Documentação": "Documentação", "Validação de Código": "Validação", "Arquiteto": "Arquiteto",
         "Code Review": "Code Review", "Testes (QualityBridge)": "QualityBridge"}


def barras(ax, rotulos, valores, cores, titulo, fmt="{:.1f}%", lim=110):
    b = ax.bar(rotulos, valores, color=cores)
    for r, v in zip(b, valores):
        ax.text(r.get_x() + r.get_width() / 2, v + lim * 0.015, fmt.format(v), ha="center", fontsize=8)
    ax.set_ylim(0, lim); ax.set_title(titulo, fontsize=10, color=AZUL, fontweight="bold")


def tempos(ax, agente, log=False):
    c = casos[casos.agente == agente]
    cores = [AZUL if p else VERMELHO for p in c.passou]
    inferior = [min(dp, m_ * 0.95) for dp, m_ in zip(c.tempo_dp_ms, c.tempo_medio_ms)]  # barra de erro não cruza o zero
    ax.bar(c.caso, c.tempo_medio_ms, yerr=[inferior, c.tempo_dp_ms], color=cores, capsize=3, error_kw={"elinewidth": 0.8})
    ax.set_ylabel("tempo médio (ms) ± DP"); ax.tick_params(axis="x", rotation=45)
    if log:
        ax.set_yscale("log")
    ax.set_title("Tempo de resposta por caso de teste", fontsize=10, color=AZUL, fontweight="bold")


def salvar(fig, nome):
    fig.tight_layout(); fig.savefig(OUT / nome, dpi=200); plt.close(fig)


def taxa(agente):
    c = casos[casos.agente == agente]
    return 100 * c.passou.mean()


# Agente 1
d = m["Documentação"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
barras(a1, ["Casos\naprovados", "Cobertura\ndocstrings", "Módulos\ndocumentados", "Acurácia\nABNT"],
       [taxa("Documentação"), d["cobertura_docstrings_depois"], d["modulos_documentados_pct"], 100 * d["acuracia_abnt"]],
       [AZUL, AZUL2, AZUL2, AZUL2], "Métricas de qualidade")
tempos(a2, "Documentação"); salvar(fig, "ag1_metricas.png")
fig, ax = plt.subplots(figsize=(4.6, 3))
barras(ax, ["Antes", "Depois"], [d["cobertura_docstrings_antes"], d["cobertura_docstrings_depois"]], [CINZA, VERDE],
       "Cobertura de docstrings do projeto")
salvar(fig, "ag1_antes_depois.png")

# Agente 2
v = m["Validação de Código"]["corpus"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
x = range(3); w = 0.38
ini = [100 * v["inicial"][k] for k in ("precisao", "recall", "f1")]
aj = [100 * v["ajustada"][k] for k in ("precisao", "recall", "f1")]
a1.bar([i - w / 2 for i in x], ini, w, color=CINZA, label="versão inicial")
a1.bar([i + w / 2 for i in x], aj, w, color=AZUL, label="versão ajustada")
for i in x:
    a1.text(i - w / 2, ini[i] + 1.5, f"{ini[i]:.1f}", ha="center", fontsize=8); a1.text(i + w / 2, aj[i] + 1.5, f"{aj[i]:.1f}", ha="center", fontsize=8)
a1.set_xticks(list(x)); a1.set_xticklabels(["Precisão", "Recall", "F1"]); a1.set_ylim(0, 115); a1.legend(fontsize=8, loc="lower right")
a1.set_title("Corpus rotulado (10 violações)", fontsize=10, color=AZUL, fontweight="bold")
tempos(a2, "Validação de Código"); salvar(fig, "ag2_metricas.png")
ad = m["Validação de Código"]["antes_depois"]
fig, ax = plt.subplots(figsize=(4.6, 3))
x = range(2)
ax.bar([i - 0.2 for i in x], [ad["violacoes_antes"], ad["cc_max_antes"]], 0.4, color=CINZA, label="antes")
ax.bar([i + 0.2 for i in x], [ad["violacoes_depois"], ad["cc_max_depois"]], 0.4, color=VERDE, label="depois")
for i, (a_, d_) in enumerate([(ad["violacoes_antes"], ad["violacoes_depois"]), (ad["cc_max_antes"], ad["cc_max_depois"])]):
    ax.text(i - 0.2, a_ + 0.2, str(a_), ha="center", fontsize=8); ax.text(i + 0.2, d_ + 0.2, str(d_), ha="center", fontsize=8)
ax.set_xticks(list(x)); ax.set_xticklabels(["Violações", "Complexidade\nciclomática máx."]); ax.legend(fontsize=8)
ax.set_title("processarPedido: antes x depois", fontsize=10, color=AZUL, fontweight="bold")
salvar(fig, "ag2_antes_depois.png")

# Agente 3
a = m["Arquiteto"]["deteccao"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
barras(a1, ["Casos\naprovados", "Precisão", "Recall", "F1"], [taxa("Arquiteto"), 100 * a["precisao"], 100 * a["recall"], 100 * a["f1"]],
       [AZUL, AZUL2, AZUL2, AZUL2], "Detecção de violações arquiteturais")
tempos(a2, "Arquiteto", log=True); salvar(fig, "ag3_metricas.png")
aa = m["Arquiteto"]["antes_depois"]
fig, ax = plt.subplots(figsize=(4.6, 3))
barras(ax, [f"Antes\n({aa['status_antes']})", f"Depois\n({aa['status_depois']})"], [aa["achados_antes"], aa["achados_depois"]],
       [CINZA, VERDE], "Achados no PR #15", fmt="{:.0f}", lim=4)
salvar(fig, "ag3_antes_depois.png")

# Agente 4
c = m["Code Review"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
barras(a1, ["Casos\naprovados", "Precisão", "Recall", "Acurácia\nseveridade", "Achados c/\nevidência"],
       [taxa("Code Review"), 100 * c["deteccao"]["precisao"], 100 * c["deteccao"]["recall"], 100 * c["acuracia_severidade"],
        c["achados_com_evidencia_pct"]], [AZUL, AZUL2, AZUL2, AZUL2, AZUL2], "Qualidade da revisão (corpus de 12 problemas)")
tempos(a2, "Code Review"); salvar(fig, "ag4_metricas.png")
fig, ax = plt.subplots(figsize=(4.6, 3))
sev = c["por_severidade"]
barras(ax, list(sev), list(sev.values()), [VERMELHO, LARANJA, "#F4D03F", AZUL2, CINZA], "Achados por severidade", fmt="{:.0f}", lim=5)
ax.tick_params(axis="x", labelsize=8)
salvar(fig, "ag4_antes_depois.png")

# Agente 5
q = m["Testes (QualityBridge)"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.4))
barras(a1, ["unittest direto\n(oráculo)", "QualityBridge\ncompleta", "QualityBridge\nrápida"],
       [q["tempo_oraculo_ms"], q["tempo_completa_ms"], q["tempo_rapida_ms"]], [CINZA, AZUL, AZUL2],
       "Tempo de execução da suíte (ms)", fmt="{:.0f} ms", lim=380)
tempos(a2, "Testes (QualityBridge)", log=True); salvar(fig, "ag5_metricas.png")

# Consolidados
fig, ax = plt.subplots(figsize=(9, 3.6))
precisao = [100 * m["Documentação"]["abnt"]["precisao"], 100 * v["ajustada"]["precisao"], 100 * a["precisao"],
            100 * c["deteccao"]["precisao"], q["fidelidade_contagens_pct"]]
recall = [100 * m["Documentação"]["abnt"]["recall"], 100 * v["ajustada"]["recall"], 100 * a["recall"],
          100 * c["deteccao"]["recall"], q["fidelidade_contagens_pct"]]
sucesso = [taxa(g) for g in AGENTES]
x = range(5); w = 0.27
for desloc, serie, cor, rot in ((-w, sucesso, AZUL, "Taxa de sucesso dos casos"), (0, precisao, AZUL2, "Precisão*"), (w, recall, CINZA, "Recall*")):
    barras_ = ax.bar([i + desloc for i in x], serie, w, color=cor, label=rot)
    for r_, s_ in zip(barras_, serie):
        ax.text(r_.get_x() + w / 2, s_ + 1, f"{s_:.0f}", ha="center", fontsize=7)
ax.set_xticks(list(x)); ax.set_xticklabels([CURTO[g] for g in AGENTES]); ax.set_ylim(0, 118); ax.set_ylabel("%")
ax.legend(fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
ax.set_title("Desempenho consolidado dos 5 agentes", fontsize=10, color=AZUL, fontweight="bold")
salvar(fig, "consolidado_barras.png")

fig, ax = plt.subplots(figsize=(9, 3.4))
dados = [amostras[amostras.agente == g].tempo_ms for g in AGENTES]
bp = ax.boxplot(dados, tick_labels=[CURTO[g] for g in AGENTES], patch_artist=True, showfliers=True,
                flierprops={"markersize": 2, "markerfacecolor": CINZA, "markeredgecolor": CINZA})
for caixa in bp["boxes"]:
    caixa.set_facecolor("#D6E0F0"); caixa.set_edgecolor(AZUL)
ax.set_yscale("log"); ax.set_ylabel("tempo por execução (ms, escala log)")
ax.set_title("Dispersão dos tempos de resposta (todas as repetições)", fontsize=10, color=AZUL, fontweight="bold")
salvar(fig, "consolidado_boxplot.png")
print(sorted(p.name for p in OUT.glob("*.png")))
