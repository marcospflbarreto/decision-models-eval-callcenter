"""Metadados de execução para o pacote de replicação: código, ambiente, dados e modelos usados.

Toda saída de geração, verificação, treino e avaliação carrega estes campos, para que um número
reportado possa ser ligado ao commit, às versões das bibliotecas e aos arquivos exatos que o produziram.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

PACOTES = ("laya", "torch", "transformers", "scikit-learn", "httpx")


def sha256(path: str | Path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state() -> dict:
    def git(*args: str) -> str | None:
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    return {"commit": git("rev-parse", "HEAD"), "alteracoes_nao_commitadas": bool(git("status", "--porcelain"))}


def versions() -> dict:
    out = {"python": sys.version.split()[0]}
    for pkg in PACOTES:
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass
    return out


def ollama_digest(base_url: str, model: str) -> str | None:
    """Digest do modelo no Ollama (o nome "gemma4:12b" pode apontar para pesos diferentes ao longo do tempo)."""
    root = base_url.rstrip("/").removesuffix("/v1")
    try:
        tags = httpx.get(f"{root}/api/tags", timeout=5).json()["models"]
    except Exception:  # noqa: BLE001 - backend não-Ollama ou fora do ar: registra sem digest
        return None
    return next((m.get("digest") for m in tags if m.get("name") == model or m.get("model") == model), None)


def run_meta(arquivos: dict[str, str | Path] | None = None, **extra) -> dict:
    return {
        "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comando": " ".join(sys.argv),
        "git": git_state(),
        "uv_lock_sha256": sha256("uv.lock"),
        "versoes": versions(),
        "plataforma": f"{platform.system()} {platform.release()} {platform.machine()}",
        "arquivos_sha256": {k: sha256(v) for k, v in (arquivos or {}).items()},
        **extra,
    }


def append_run(path: str | Path, meta: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
