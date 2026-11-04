#!/usr/bin/env python3
"""Painel de progresso da rotulagem por LLM: download dos modelos e itens rotulados. Atualiza a cada 5 s.

Uso: python3 scripts/progresso.py [--once]
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

MODELOS = [
    ("Mistral Small 24B", "mistral-small3.1:24b", "mistral-small3.1-24b", "logs/rotular-mistral.log"),
    ("Llama 3.3 70B", "llama3.3:70b", "llama3.3-70b", "logs/rotular-llama.log"),
    ("gpt-oss 20B (desempate)", "gpt-oss:20b", "gpt-oss-20b", "logs/rotular-gptoss.log"),
]
PULL_LOG = Path("logs/pull-anotadores.log")
EXPORT = Path("data/consumerbr/auditoria/export_llm")
TOTAL = 200


def barra(pct: float, n: int = 28) -> str:
    cheio = round(n * pct / 100)
    return "█" * cheio + "░" * (n - cheio) + f" {pct:3.0f}%"


def fim(path: Path, n: int = 65536) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - n))
        return f.read().decode("utf-8", "ignore")


def instalados() -> str:
    try:
        return subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001 - Ollama fora do ar: painel continua
        return ""


def download() -> str:
    """Último progresso do `ollama pull` no log."""
    m = re.findall(r"(\d+)%[^\d]*?([\d.]+ [KMG]?B)/\s*([\d.]+ [KMG]?B)\s+([\d.]+ [KMG]?B/s)\s+(\S+?)\x1b", fim(PULL_LOG))
    if not m:
        return "    baixando..."
    pct, feito, total, vel, eta = m[-1]
    return f"    {barra(float(pct))}  {feito} de {total}, {vel}, faltam {eta}"


def rotulagem(slug: str, log: str) -> str:
    arq = EXPORT / f"{slug}.json"
    try:
        n = len(json.loads(arq.read_text(encoding="utf-8"))["itens"])
    except Exception:  # noqa: BLE001 - arquivo ainda não existe ou está sendo gravado
        n = 0
    m = re.findall(r"\[[^<\]]*<([^,\]]+),\s*([^\]]+)\]", fim(Path(log)))
    extra = f"  faltam {m[-1][0]}, {m[-1][1]}" if m and n < TOTAL else ""
    return f"    {barra(100 * n / TOTAL)}  {n}/{TOTAL} reclamações{extra}"


def tela() -> str:
    lista = instalados()
    linhas = [f"Rotulagem por LLM  ·  {time.strftime('%H:%M:%S')}", ""]
    baixando = False
    for nome, tag, slug, log in MODELOS:
        linhas.append(nome)
        if tag in lista:
            linhas.append("    download concluído")
            linhas.append(rotulagem(slug, log))
        elif not baixando:
            baixando = True
            linhas.append(download())
        else:
            linhas.append("    na fila")
        linhas.append("")
    rodando = subprocess.run(["pgrep", "-f", "ollama pull|callsim.rotular_llm"], capture_output=True).stdout
    if not rodando:
        linhas.append("Nenhum processo rodando: terminou ou foi interrompido.")
    return "\n".join(linhas)


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(tela())
    else:
        while True:
            print("\033[2J\033[H" + tela() + "\n\nCtrl+C fecha o painel; o trabalho continua.", flush=True)
            time.sleep(5)
