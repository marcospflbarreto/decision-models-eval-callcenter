"""Avaliação de negócio de um checkpoint Laya no conjunto de teste.

Faz a classificação como em produção: primeiro assunto, criticidade e risco BACEN; depois o
sub-assunto, perguntado só entre as opções do assunto PREVISTO (então um erro de assunto
também conta como erro de sub-assunto).

Grava logs/eval/<conjunto>/<modelo>/{preds.jsonl, metrics.json} (ver metrics.py) e imprime a
comparação entre os modelos passados, com IC 95% e McNemar contra o primeiro.

Uso:
    uv run callsim-laya-eval --model models/laya-callcenter-v1 --model convaiinnovations/laya-multilingual
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import laya

from .laya_data import q_assunto, q_criticidade, q_risco_bacen, q_sub_assunto
from .meta import run_meta
from .metrics import LIMIAR_BACEN, write_run
from .sampler import NIVEIS, load_taxonomy


def level(ans: dict) -> int:
    probs = ans["probabilities"]
    return max(range(len(NIVEIS)), key=lambda i: probs.get(str(i), 0.0))


def predict(model_id: str, records: list[dict], tax: dict, device: str) -> tuple[list[dict], float]:
    agent = laya.load(model_id, device=device)
    states = [r["transcricao"] for r in records]
    agent.predict_batch(states[:2], {"assunto": q_assunto(tax)}, batch_size=2)  # aquecimento

    t0 = time.perf_counter()
    step1 = agent.predict_batch(
        states,
        {"assunto": q_assunto(tax), "criticidade": q_criticidade(tax), "risco_bacen": q_risco_bacen()},
        batch_size=8,
    )
    by_assunto = defaultdict(list)
    for i, res in enumerate(step1):
        by_assunto[res["answers"]["assunto"]["choice"]].append(i)
    sub_pred: dict[int, dict] = {}
    for assunto, idx in by_assunto.items():
        out = agent.predict_batch([states[i] for i in idx], {"sub_assunto": q_sub_assunto(tax, assunto)}, batch_size=8)
        for i, res in zip(idx, out):
            sub_pred[i] = res["answers"]["sub_assunto"]
    ms = (time.perf_counter() - t0) * 1000 / len(records)

    preds = []
    for i, r in enumerate(records):
        a = step1[i]["answers"]
        lab = r["labels"]
        preds.append({
            "id": r["id"],
            "true": {**lab, "criticidade": NIVEIS.index(lab["criticidade"]) if lab.get("criticidade") else None},
            "pred": {
                "assunto": a["assunto"]["choice"],
                "assunto_conf": a["assunto"]["answer_confidence"],
                "assunto_probs": a["assunto"]["probabilities"],
                "sub_assunto": sub_pred[i]["choice"],
                "sub_assunto_conf": sub_pred[i]["answer_confidence"],
                "criticidade": level(a["criticidade"]),
                "criticidade_conf": a["criticidade"]["answer_confidence"],
                "criticidade_probs": [a["criticidade"]["probabilities"].get(str(k), 0.0) for k in range(len(NIVEIS))],
                "p_bacen": a["risco_bacen"]["noul"],
            },
        })
    return preds, ms


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", action="append", required=True, help="checkpoint local ou id do Hub (repita para comparar)")
    p.add_argument("--test", default="data/splits/test.jsonl")
    p.add_argument("--taxonomy", default="config/taxonomy.yaml")
    p.add_argument("--device", default="mps")
    p.add_argument("--limiar-bacen", type=float, default=LIMIAR_BACEN)
    p.add_argument("--out-dir", default="logs/eval", help="grava em <out-dir>/<conjunto>/<modelo>")
    args = p.parse_args()

    tax = load_taxonomy(args.taxonomy)
    test = Path(args.test)
    records = [json.loads(line) for line in test.open(encoding="utf-8") if line.strip()]
    base = Path(args.out_dir) / f"{test.parent.name}-{test.stem}"
    dirs = []
    for m in args.model:
        preds, ms = predict(m, records, tax, args.device)
        d = base / Path(m).name
        cfg = Path(m) / "train_meta.json"
        meta = run_meta({"test": test, "taxonomia": args.taxonomy}, modelo=m, device=args.device,
                        ms_por_conversa=ms, treino=json.loads(cfg.read_text()) if cfg.exists() else None)
        write_run(d, preds, meta, args.limiar_bacen)
        print(f"{m}: {ms:.1f} ms/conversa -> {d}", flush=True)
        dirs.append(str(d))
    subprocess.run([sys.executable, "-m", "callsim.metrics", *dirs, "--limiar-bacen", str(args.limiar_bacen)], check=True)


if __name__ == "__main__":
    main()
