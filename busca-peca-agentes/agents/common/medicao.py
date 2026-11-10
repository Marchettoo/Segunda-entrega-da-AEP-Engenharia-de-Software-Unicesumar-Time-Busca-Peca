"""Medição de tempo de resposta e pico de memória (indicadores ODS 12)."""
import statistics
import time
import tracemalloc


def medir(funcao, repeticoes: int = 30):
    """Executa `funcao` N vezes; retorna (ultimo_resultado, estatisticas)."""
    tempos = []
    resultado = None
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        resultado = funcao()
        tempos.append((time.perf_counter() - inicio) * 1000)
    tracemalloc.start()
    funcao()
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    est = {
        "n": repeticoes,
        "media_ms": statistics.mean(tempos),
        "dp_ms": statistics.stdev(tempos) if repeticoes > 1 else 0.0,
        "mediana_ms": statistics.median(tempos),
        "min_ms": min(tempos),
        "max_ms": max(tempos),
        "pico_memoria_kb": pico / 1024,
        "amostras_ms": tempos,
    }
    return resultado, est
