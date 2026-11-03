"""Remove quase-duplicatas, mostra a distribuição dos rótulos e divide em train/calib/test.

Uso:
    uv run callsim-dataset --filtrar
    uv run callsim-dataset --filtrar --split-por cenario --out data/splits-cenario
Com --filtrar, mantém só conversas que a verificação cega (callsim-verify) confirmou
na versão atual da taxonomia; as ainda não verificadas ficam de fora.

--split-por cenario monta um teste de generalização: em cada sub-assunto, um cenário inteiro
(sorteado por hash) vai só para o teste, então o modelo é avaliado em situações que nunca viu
no treino, e não em variações do mesmo cenário. Com --filtrar, também grava test_nao_filtrado.jsonl:
o filtro do juiz remove casos ambíguos e deixaria o teste mais fácil que a realidade.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from .meta import append_run, run_meta
from .sampler import load_taxonomy
from .verify import agrees, load_verdicts

N_PERM, BANDS = 64, 16  # LSH: 16 bandas de 4 linhas -> pega pares com Jaccard >~ 0.6


def shingles(text: str, k: int = 5) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i : i + k]) for i in range(max(1, len(words) - k + 1))}


def minhash(sh: set[str]) -> list[int]:
    return [
        min(int.from_bytes(hashlib.blake2b(f"{p}:{s}".encode(), digest_size=8).digest(), "big") for s in sh)
        for p in range(N_PERM)
    ]


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b)


def dedup(records: list[dict], threshold: float) -> tuple[list[dict], int]:
    rows = N_PERM // BANDS
    buckets: dict[tuple, list[int]] = defaultdict(list)
    sh = [shingles(r["transcricao"]) for r in records]
    keep, dropped = [], 0
    for i, s in enumerate(sh):
        sig = minhash(s)
        keys = [(b, tuple(sig[b * rows : (b + 1) * rows])) for b in range(BANDS)]
        cands = {j for k in keys for j in buckets[k]}
        if any(jaccard(s, sh[j]) >= threshold for j in cands):
            dropped += 1
            continue
        for k in keys:
            buckets[k].append(i)
        keep.append(records[i])
    return keep, dropped


def _u(key: str) -> float:
    return int.from_bytes(hashlib.blake2b(key.encode(), digest_size=8).digest(), "big") / 2**64


def test_cenarios(tax: dict, seed: int) -> set[tuple[str, str]]:
    """Um cenário por sub-assunto, sorteado por hash: estável enquanto a taxonomia não mudar."""
    out = set()
    for a in tax["assuntos"].values():
        for sub, d in a["sub_assuntos"].items():
            textos = [c["t"] if isinstance(c, dict) else c for c in d["cenarios"]]
            out.add((sub, min(textos, key=lambda t: _u(f"{seed}:{sub}:{t}"))))
    return out


def split(records: list[dict], calib: float, test: float, seed: int, cenarios_teste: set | None = None) -> dict[str, list[dict]]:
    # O split de cada conversa é um hash do id: ao gerar mais conversas depois, as antigas
    # nunca trocam de split (nada do teste vaza para o treino entre rodadas). Com milhares
    # de exemplos por estrato, as proporções por (sub_assunto, criticidade) se mantêm.
    out = {"train": [], "calib": [], "test": []}
    for r in records:
        u = _u(f"{seed}:{r['id']}")
        if cenarios_teste is not None:
            no_teste = (r["spec"]["sub_assunto"], r["spec"]["cenario"]) in cenarios_teste
            out["test" if no_teste else "calib" if u < calib else "train"].append(r)
        else:
            out["test" if u < test else "calib" if u < test + calib else "train"].append(r)
    rng = random.Random(seed)
    for v in out.values():
        rng.shuffle(v)
    return out


def report(records: list[dict]) -> None:
    for key in ("assunto", "sub_assunto", "criticidade", "risco_bacen"):
        c = Counter(r["labels"][key] for r in records)
        print(f"\n{key}:")
        for k, v in c.most_common():
            print(f"  {str(k):28s} {v:6d}  {v / len(records):6.1%}")
    n_turns = sorted(len(r["turnos"]) for r in records)
    n_chars = sorted(len(r["transcricao"]) for r in records)
    mid = len(records) // 2
    print(f"\nturnos (mediana): {n_turns[mid]}   caracteres (mediana/max): {n_chars[mid]}/{n_chars[-1]}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw", default="data/raw/conversations.jsonl")
    p.add_argument("--out", default="data/splits")
    p.add_argument("--dedup-threshold", type=float, default=0.6)
    p.add_argument("--calib", type=float, default=0.1)
    p.add_argument("--test", type=float, default=0.1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--split-por", choices=["id", "cenario"], default="id",
                   help="cenario: cenários inteiros só no teste (generalização para situações novas)")
    p.add_argument("--filtrar", action="store_true", help="descarta conversas em que o juiz cego discorda do rótulo")
    p.add_argument("--verdicts", default="data/raw/verdicts.jsonl")
    p.add_argument("--taxonomy", default="config/taxonomy.yaml")
    args = p.parse_args()

    tax = load_taxonomy(args.taxonomy)
    cenarios = test_cenarios(tax, args.seed) if args.split_por == "cenario" else None
    records = [json.loads(line) for line in Path(args.raw).open(encoding="utf-8") if line.strip()]
    todas = records
    if args.filtrar:
        verdicts = load_verdicts(Path(args.verdicts), tax.get("versao", 1))
        sem = sum(r["id"] not in verdicts for r in records)
        ok = [r for r in records if r["id"] in verdicts and agrees(r["labels"], verdicts[r["id"]])]
        print(f"filtro: {len(ok)} mantidas, {len(records) - len(ok) - sem} discordantes, {sem} ainda sem veredicto")
        records = ok
    records, dropped = dedup(records, args.dedup_threshold)
    print(f"{len(records)} conversas após remover {dropped} quase-duplicatas")
    report(records)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    splits = split(records, args.calib, args.test, args.seed, cenarios)
    if args.filtrar:
        # Mesmo critério de split, sem o filtro do juiz (só o dedup e a versão atual da taxonomia):
        # mede quanto o filtro facilita o teste.
        atuais = [r for r in todas if r["gen"].get("taxonomia", 1) == tax.get("versao", 1)]
        splits["test_nao_filtrado"] = split(dedup(atuais, args.dedup_threshold)[0], args.calib, args.test, args.seed, cenarios)["test"]
    for name, rows in splits.items():
        with (out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name}: {len(rows)}")
    if cenarios:
        print("cenários só no teste:", *sorted(f"{s}: {c}" for s, c in cenarios), sep="\n  ")
    append_run(out / "runs.jsonl", run_meta({"raw": args.raw, "verdicts": args.verdicts, "taxonomia": args.taxonomy},
                                            args=vars(args), tamanhos={k: len(v) for k, v in splits.items()}))


if __name__ == "__main__":
    main()
