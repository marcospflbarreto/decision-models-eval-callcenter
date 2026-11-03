"""Gera conversas sintéticas rotuladas.

Uso:
    uv run callsim-generate --n 30000 --max-minutes 60
Incremental: ids que já estão no arquivo de saída são pulados, então basta
rodar o mesmo comando de novo para continuar de onde parou. Falhas ficam em
*.errors.jsonl e são tentadas de novo na próxima execução.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from pathlib import Path

from tqdm import tqdm

from .llm import ChatClient
from .meta import append_run, ollama_digest, run_meta
from .prompts import build_messages
from .sampler import Spec, load_taxonomy, sample_spec

FALANTES = {"atendente", "cliente"}
# Palavras que indicam vazamento do rótulo para o texto.
VAZAMENTO = re.compile(r"\b(criticidade|n[ií]vel de gravidade|categoria do (caso|atendimento))\b", re.I)


def check(out: dict, spec: Spec) -> list[dict]:
    turnos = out.get("turnos")
    if not isinstance(turnos, list) or len(turnos) < 4:
        raise ValueError("menos de 4 turnos")
    clean = []
    for t in turnos:
        falante = str(t.get("falante", "")).strip().lower()
        texto = str(t.get("texto", "")).strip()
        if falante not in FALANTES or not texto:
            raise ValueError(f"turno inválido: {t!r}")
        clean.append({"falante": falante, "texto": texto})
    full = " ".join(t["texto"] for t in clean)
    if VAZAMENTO.search(full):
        raise ValueError("rótulo vazou para o texto")
    if not spec.risco_bacen and not spec.distrator_bacen and re.search(r"banco central|bacen|ouvidoria|procon", full, re.I):
        raise ValueError("menção regulatória fora da especificação")
    return clean


def to_record(spec: Spec, turnos: list[dict], out: dict, model: str, usage: dict, versao: int) -> dict:
    return {
        "id": spec.id,
        "labels": {
            "assunto": spec.assunto,
            "sub_assunto": spec.sub_assunto,
            "criticidade": spec.criticidade,
            "risco_bacen": spec.risco_bacen,
        },
        "transcricao": "\n".join(f"{t['falante'].capitalize()}: {t['texto']}" for t in turnos),
        "resumo_atendente": str(out.get("resumo_atendente", "")).strip(),
        "turnos": turnos,
        "spec": spec.to_dict(),
        "gen": {"model": model, "usage": usage, "taxonomia": versao},
    }


async def generate_one(client: ChatClient, tax: dict, spec: Spec, retries: int) -> dict:
    sub_desc = tax["assuntos"][spec.assunto]["sub_assuntos"][spec.sub_assunto]["descricao"]
    msgs = build_messages(spec, sub_desc, tax["criticidade"]["definicoes"])
    last = None
    for _ in range(retries + 1):
        try:
            out, usage = await client.json_chat(msgs)
            return to_record(spec, check(out, spec), out, client.model, usage, tax.get("versao", 1))
        except Exception as e:  # noqa: BLE001 - qualquer falha vira nova tentativa
            last = e
    raise RuntimeError(f"{spec.id}: {last}")


def done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    # Uma execução interrompida à força pode deixar a última linha pela metade: descarta.
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        path.write_bytes(data[: data.rfind(b"\n") + 1])
    return {json.loads(line)["id"] for line in path.open(encoding="utf-8") if line.strip()}


async def run(args: argparse.Namespace) -> None:
    tax = load_taxonomy(args.taxonomy)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    err_path = out_path.with_suffix(".errors.jsonl")

    skip = done_ids(out_path)
    specs = [s for i in range(args.start, args.start + args.n) if (s := sample_spec(tax, i, args.seed)).id not in skip]
    print(f"{len(skip)} já geradas; gerando {len(specs)} com {args.model} @ {args.base_url}")

    append_run(out_path.parent / "runs.jsonl", run_meta({"taxonomia": args.taxonomy}, etapa="generate", args=vars(args),
                                     modelo_digest=ollama_digest(args.base_url, args.model)))
    client = ChatClient(args.base_url, args.model)
    queue: asyncio.Queue[Spec] = asyncio.Queue()
    for s in specs:
        queue.put_nowait(s)
    bar = tqdm(total=len(specs), unit="conv")
    tokens = ok = 0
    t0 = time.time()
    deadline = t0 + args.max_minutes * 60 if args.max_minutes else float("inf")

    with out_path.open("a", encoding="utf-8") as fout, err_path.open("a", encoding="utf-8") as ferr:

        async def worker() -> None:
            nonlocal tokens, ok
            # Ao atingir o limite de tempo, cada worker termina a conversa em andamento e para.
            while not queue.empty() and time.time() < deadline:
                spec = queue.get_nowait()
                try:
                    rec = await generate_one(client, tax, spec, args.retries)
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fout.flush()
                    tokens += rec["gen"]["usage"].get("completion_tokens", 0)
                    ok += 1
                except Exception as e:  # noqa: BLE001
                    ferr.write(json.dumps({"id": spec.id, "erro": str(e)}, ensure_ascii=False) + "\n")
                    ferr.flush()
                bar.update(1)
                bar.set_postfix(tok_s=f"{tokens / (time.time() - t0):.0f}")

        await asyncio.gather(*(worker() for _ in range(args.concurrency)))
    bar.close()
    await client.aclose()
    mins = (time.time() - t0) / 60
    print(f"{ok} novas em {mins:.0f} min ({ok / mins * 60:.0f}/h); total no arquivo: {len(done_ids(out_path))}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=100, help="quantidade de conversas")
    p.add_argument("--start", type=int, default=0, help="índice inicial (para dividir entre máquinas)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="data/raw/conversations.jsonl")
    p.add_argument("--taxonomy", default="config/taxonomy.yaml")
    p.add_argument("--base-url", default="http://localhost:11435/v1", help="endpoint OpenAI-compatível (scripts/ollama-fast.sh)")
    p.add_argument("--model", default="gemma4:12b")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--max-minutes", type=float, default=0, help="para de pegar novas conversas após N minutos (0 = sem limite)")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
