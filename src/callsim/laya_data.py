"""Converte as conversas em linhas de treino/avaliação do Laya ({state, questions, expected}).

Quatro perguntas por conversa:
- assunto (choice, 4 opções)
- sub_assunto (choice só entre os sub-assuntos do assunto: classificação em 2 passos,
  porque o Laya perde precisão com muitas opções de uma vez)
- criticidade (score ordinal: normal < importante < grave < BACEN)
- risco_bacen (noul)

Uso:
    uv run callsim-laya-data --splits data/splits --out data/laya
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .sampler import NIVEIS, load_taxonomy

INSTR_BACEN = (
    "O cliente registrou ou ameaça registrar reclamação formal (Banco Central, Ouvidoria, Procon ou Justiça), "
    "ou o banco nega um direito regulatório do cliente nesta ligação?"
)


def q_assunto(tax: dict) -> dict:
    return {
        "type": "choice",
        "instructions": "Qual é o assunto principal desta ligação de call center bancário?",
        "criteria": {k: v["curta"] for k, v in tax["assuntos"].items()},
    }


def q_sub_assunto(tax: dict, assunto: str) -> dict:
    a = tax["assuntos"][assunto]
    return {
        "type": "choice",
        "instructions": f"Assunto: {a['curta']}. Qual é o problema específico do cliente?",
        "criteria": {k: v["curta"] for k, v in a["sub_assuntos"].items()},
    }


def q_criticidade(tax: dict) -> dict:
    curtas = tax["criticidade"]["curtas"]
    return {
        "type": "score",
        "instructions": "Qual a gravidade do problema relatado pelo cliente?",
        "criteria": [f"{n}: {curtas[n]}" for n in NIVEIS],
    }


def q_risco_bacen() -> dict:
    return {"type": "noul", "instructions": INSTR_BACEN}


def to_row(tax: dict, rec: dict) -> dict:
    lab = rec["labels"]
    return {
        "id": rec["id"],
        "state": rec["transcricao"],
        "questions": {
            "assunto": q_assunto(tax),
            "sub_assunto": q_sub_assunto(tax, lab["assunto"]),
            "criticidade": q_criticidade(tax),
            "risco_bacen": q_risco_bacen(),
        },
        "expected": {
            "assunto": lab["assunto"],
            "sub_assunto": lab["sub_assunto"],
            "criticidade": NIVEIS.index(lab["criticidade"]),
            "risco_bacen": lab["risco_bacen"],
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--splits", default="data/splits")
    p.add_argument("--out", default="data/laya")
    p.add_argument("--taxonomy", default="config/taxonomy.yaml")
    args = p.parse_args()

    tax = load_taxonomy(args.taxonomy)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # O laya-train separa sozinho uma fatia de calibração do arquivo de treino,
    # então train + calib vão juntos; test fica intocado para a prova final.
    plan = {"train": ["train", "calib"], "test": ["test"]}
    for name, sources in plan.items():
        rows = [
            to_row(tax, json.loads(line))
            for src in sources
            for line in (Path(args.splits) / f"{src}.jsonl").open(encoding="utf-8")
            if line.strip()
        ]
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name}: {len(rows)} conversas, {4 * len(rows)} perguntas")


if __name__ == "__main__":
    main()
