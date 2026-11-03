"""Apura a auditoria cega das 200 reclamações do ConsumerBR (página "Auditoria ConsumerBR").

Entrada: os documentos `anotacoes/<pessoa>` da página, exportados com
    ArtifactData list --collection anotacoes --out_dir data/consumerbr/auditoria/export
e a amostra local com o rótulo prata (data/consumerbr/auditoria/amostra.jsonl).

Mede:
- concordância de cada anotador com o rótulo prata (assunto e sub-assunto) = ruído do rótulo prata;
- concordância entre anotadores (kappa de Cohen; kappa ponderado quadrático na criticidade), se houver 2+;
- quanto da amostra fica fora da taxonomia.
Grava gold.jsonl (consenso; com 1 anotador, as respostas dele) no formato dos splits, com
criticidade e risco BACEN, para usar em `callsim-laya-eval --test`.

Uso:
    uv run python -m callsim.auditoria
"""

from __future__ import annotations

import argparse
import collections
import json
from itertools import combinations
from pathlib import Path

from .sampler import NIVEIS
from .stats import wilson


def kappa(a: list, b: list, ordinal: list | None = None) -> float:
    """Kappa de Cohen; com `ordinal`, ponderado quadrático (para a criticidade)."""
    cats = ordinal or sorted(set(a) | set(b), key=str)
    k, n = len(cats), len(a)
    if n == 0 or k < 2:
        return float("nan")
    ix = {c: i for i, c in enumerate(cats)}
    w = [[((i - j) / (k - 1)) ** 2 if ordinal else float(i != j) for j in range(k)] for i in range(k)]
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[ix[x]][ix[y]] += 1 / n
    pa = [sum(r) for r in obs]
    pb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    do = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    de = sum(w[i][j] * pa[i] * pb[j] for i in range(k) for j in range(k))
    return 1 - do / de if de else float("nan")


def load_anotacoes(pasta: Path) -> dict[str, dict]:
    out = {}
    for f in sorted(pasta.rglob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        corpo = doc.get("data", doc)
        if corpo.get("itens"):
            out[doc.get("id", f.stem)] = corpo["itens"]
    return out


def _pct(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]" if n else "—"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--amostra", default="data/consumerbr/auditoria/amostra.jsonl")
    p.add_argument("--export", default="data/consumerbr/auditoria/export")
    p.add_argument("--out", default="data/consumerbr/auditoria/gold.jsonl")
    args = p.parse_args()

    amostra = {r["item"]: r for r in map(json.loads, open(args.amostra, encoding="utf-8"))}
    anot = load_anotacoes(Path(args.export))
    if not anot:
        raise SystemExit(f"nenhuma anotação em {args.export}: exporte a coleção anotacoes da página primeiro")
    print(f"{len(anot)} anotador(es): " + ", ".join(f"{a[:10]}… ({len(v)} itens)" for a, v in anot.items()))

    for pessoa, itens in anot.items():
        ok_a = ok_s = n_s = fora = 0
        conf = collections.Counter()
        for item, r in itens.items():
            prata = amostra[item]["labels"]
            fora += r["assunto"] == "fora"
            ok_a += r["assunto"] == prata["assunto"]
            if prata["sub_assunto"]:
                n_s += 1
                ok_s += r["sub"] == prata["sub_assunto"]
            if r["assunto"] != prata["assunto"]:
                conf[(prata["assunto"], r["assunto"])] += 1
        n = len(itens)
        print(f"\n== {pessoa[:10]}… vs rótulo prata")
        print(f"  assunto igual ao prata       {_pct(ok_a, n)}")
        print(f"  sub-assunto igual ao prata   {_pct(ok_s, n_s)}")
        print(f"  fora da taxonomia            {_pct(fora, n)}")
        print(f"  com dúvida                   {_pct(sum(r['duvida'] for r in itens.values()), n)}")
        print(f"  criticidade                  {dict(collections.Counter(r['crit'] for r in itens.values()))}")
        print(f"  risco BACEN                  {_pct(sum(r['bacen'] for r in itens.values()), n)}")
        print("  maiores divergências (prata -> anotador):", conf.most_common(5))

    if len(anot) >= 2:
        print("\n== concordância entre anotadores (itens rotulados por ambos)")
        for (pa, a), (pb, b) in combinations(anot.items(), 2):
            comuns = sorted(set(a) & set(b))
            ka = kappa([a[i]["assunto"] for i in comuns], [b[i]["assunto"] for i in comuns])
            ks = kappa([a[i]["sub"] for i in comuns], [b[i]["sub"] for i in comuns])
            kc = kappa([a[i]["crit"] for i in comuns], [b[i]["crit"] for i in comuns], NIVEIS)
            kb = kappa([a[i]["bacen"] for i in comuns], [b[i]["bacen"] for i in comuns])
            print(f"  {pa[:8]}… x {pb[:8]}… n={len(comuns)}: kappa assunto {ka:.2f}, sub {ks:.2f}, "
                  f"criticidade (ponderado) {kc:.2f}, BACEN {kb:.2f}")

    # Consenso: maioria por campo; empate fica com o primeiro anotador (com 2, só entra o que concordam).
    gold = []
    for item, base in amostra.items():
        rs = [v[item] for v in anot.values() if item in v]
        if not rs:
            continue
        def maioria(campo):
            c = collections.Counter(r[campo] for r in rs).most_common()
            return c[0][0] if len(rs) != 2 or c[0][1] == 2 else None
        assunto, sub, crit, bacen = maioria("assunto"), maioria("sub"), maioria("crit"), maioria("bacen")
        if assunto in (None, "fora"):
            continue
        gold.append({
            "id": base["id"], "item": item,
            "labels": {"assunto": assunto, "sub_assunto": sub if sub not in (None, "nenhum", "fora") else None,
                       "criticidade": crit, "risco_bacen": bacen},
            "transcricao": base["transcricao"], "fonte": {**base["fonte"], "rotulo_prata": base["labels"],
                                                          "anotadores": len(rs)},
        })
    with open(args.out, "w", encoding="utf-8") as fh:
        for g in gold:
            fh.write(json.dumps(g, ensure_ascii=False) + "\n")
    print(f"\n-> {args.out}: {len(gold)} reclamações com rótulo gold (fora da taxonomia e empates ficam de fora)")


if __name__ == "__main__":
    main()
