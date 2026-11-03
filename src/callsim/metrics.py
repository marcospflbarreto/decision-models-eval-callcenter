"""Métricas de negócio, com intervalo de confiança, a partir das predições por item.

Todo avaliador (Laya, baseline TF-IDF, Jev) grava um diretório com:
    preds.jsonl   uma linha por conversa: {id, true: {...}, pred: {...}}
    metrics.json  métricas com IC 95% + metadados da execução
As predições brutas ficam guardadas, então qualquer métrica nova pode ser recalculada depois
sem rodar o modelo de novo, e dois modelos podem ser comparados item a item.

Comparação (cada argumento é um glob; vários diretórios no mesmo glob = seeds do mesmo sistema):
    uv run callsim-compare logs/eval/test/laya-callcenter-v1 'logs/eval/test/laya-s*' logs/eval/test/tfidf-logreg
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import statistics
from pathlib import Path

from .sampler import NIVEIS
from .stats import bootstrap, ece, holm, macro_f1, mcnemar, wilson

LIMIAR_BACEN = 0.5


def item_flags(p: dict, limiar: float = LIMIAR_BACEN) -> dict:
    """Acerto por item. Um rótulo ausente (None, ex.: dados reais sem criticidade) gera flag None,
    e o item fica fora das métricas que dependem dele."""
    t, q = p["true"], p["pred"]
    lv_t, lv_p = t.get("criticidade"), q["criticidade"]
    tem_crit = lv_t is not None
    tem_bacen = t.get("risco_bacen") is not None
    return {
        "assunto_ok": q["assunto"] == t["assunto"],
        "sub_ok": q["sub_assunto"] == t["sub_assunto"] if t.get("sub_assunto") is not None else None,
        "crit_ok": lv_p == lv_t if tem_crit else None,
        "crit_near": abs(lv_p - lv_t) <= 1 if tem_crit else None,
        "crit_under": lv_p < lv_t if tem_crit else None,
        "grave_true": lv_t >= 2 if tem_crit else None,
        "grave_pred": lv_p >= 2,
        "bacen_true": t["risco_bacen"] if tem_bacen else None,
        # Regra de produção: BACEN se a criticidade prevista é BACEN OU a probabilidade passa do limiar.
        "bacen_pred": lv_p == 3 or q["p_bacen"] >= limiar,
        "noul_pred": q["p_bacen"] >= limiar,
    }


def _prop(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"valor": k / n if n else math.nan, "ic95": [lo, hi], "k": k, "n": n}


def _boot(fn, n: int) -> dict:
    if n == 0:
        return {"valor": math.nan, "ic95": [math.nan, math.nan], "n": 0}
    lo, hi = bootstrap(fn, n)
    return {"valor": fn(list(range(n))), "ic95": [lo, hi], "n": n}


def compute(preds: list[dict], limiar: float = LIMIAR_BACEN) -> dict:
    f = [item_flags(p, limiar) for p in preds]
    n = len(f)
    t = [p["true"] for p in preds]
    q = [p["pred"] for p in preds]

    def count(key: str, where: str | None = None, value: bool = True) -> tuple[int, int]:
        sel = [x for x in f if x[key] is not None and (where is None or x[where] == value)]
        return sum(x[key] for x in sel), len(sel)

    i_sub = [i for i, x in enumerate(f) if x["sub_ok"] is not None]
    i_crit = [i for i, x in enumerate(f) if x["crit_ok"] is not None]
    pos = [x for x in f if x["bacen_true"]]
    flagged = [x for x in f if x["bacen_pred"] and x["bacen_true"] is not None]

    def sub(fn, idx_validos: list[int]):
        # Bootstrap só sobre os itens que têm o rótulo.
        return lambda idx: fn([idx_validos[i] for i in idx])

    m = {
        "assunto": _prop(*count("assunto_ok")),
        "sub_assunto_2_passos": _prop(*count("sub_ok")),
        "sub_assunto_macro_f1": _boot(sub(lambda idx: macro_f1([t[i]["sub_assunto"] for i in idx], [q[i]["sub_assunto"] for i in idx]), i_sub), len(i_sub)),
        "criticidade_exata": _prop(*count("crit_ok")),
        "criticidade_macro_f1": _boot(sub(
            lambda idx: macro_f1([t[i]["criticidade"] for i in idx], [q[i]["criticidade"] for i in idx], range(len(NIVEIS))), i_crit),
            len(i_crit)),
        "criticidade_mais_menos_1": _prop(*count("crit_near")),
        "criticidade_subestimada": _prop(*count("crit_under")),
        "grave_ou_bacen_recall": _prop(*count("grave_pred", "grave_true")),
        "bacen_recall": _prop(sum(x["bacen_pred"] for x in pos), len(pos)),
        "bacen_precisao": _prop(sum(x["bacen_true"] for x in flagged), len(flagged)),
        "bacen_recall_so_noul": _prop(sum(x["noul_pred"] for x in pos), len(pos)),
    }
    if all(x.get("assunto_conf") is not None for x in q):
        m["ece_assunto"] = _boot(lambda idx: ece([q[i]["assunto_conf"] for i in idx], [f[i]["assunto_ok"] for i in idx]), n)
        m["ece_criticidade"] = _boot(sub(lambda idx: ece([q[i]["criticidade_conf"] for i in idx], [f[i]["crit_ok"] for i in idx]), i_crit), len(i_crit))
    confusao = [[0] * len(NIVEIS) for _ in NIVEIS]
    for i in i_crit:
        confusao[t[i]["criticidade"]][q[i]["criticidade"]] += 1
    m = {k: v for k, v in m.items() if v["n"]}  # métricas sem nenhum item rotulado ficam de fora
    return {"n": n, "bacen_n": len(pos), "limiar_bacen": limiar, "metricas": m,
            "criticidade_confusao": {"linhas_rotulo_colunas_predicao": NIVEIS, "matriz": confusao}}


def write_run(out_dir: str | Path, preds: list[dict], meta: dict, limiar: float = LIMIAR_BACEN) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "preds.jsonl").open("w", encoding="utf-8") as fh:
        for p in preds:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    res = {**compute(preds, limiar), "meta": meta}
    (out / "metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def load_preds(run_dir: str | Path) -> list[dict]:
    return [json.loads(line) for line in (Path(run_dir) / "preds.jsonl").open(encoding="utf-8") if line.strip()]


# Métricas pareadas (acerto por item) usadas no McNemar.
PAREADAS = {"assunto": "assunto_ok", "sub_assunto_2_passos": "sub_ok", "criticidade_exata": "crit_ok"}


def paired(ref: list[dict], other: list[dict], limiar: float = LIMIAR_BACEN) -> dict:
    """McNemar por métrica (com Holm entre as métricas); exige as mesmas conversas nos dois."""
    by_id = {p["id"]: p for p in other}
    if set(by_id) != {p["id"] for p in ref}:
        raise SystemExit("as execuções comparadas não usam o mesmo conjunto de teste")
    fa = [item_flags(p, limiar) for p in ref]
    fb = [item_flags(by_id[p["id"]], limiar) for p in ref]
    # Decisão BACEN correta (acerto tanto nos positivos quanto nos negativos).
    pares = {k: ([x[v] for x in fa], [x[v] for x in fb]) for k, v in PAREADAS.items()}
    pares["decisao_bacen"] = ([None if x["bacen_true"] is None else x["bacen_pred"] == x["bacen_true"] for x in fa],
                              [None if x["bacen_true"] is None else x["bacen_pred"] == x["bacen_true"] for x in fb])
    # Só os itens com o rótulo daquela métrica; métricas sem rótulo algum ficam de fora.
    pares = {k: tuple(zip(*[(x, y) for x, y in zip(a, b) if x is not None and y is not None])) for k, (a, b) in pares.items()}
    out = {k: mcnemar(list(v[0]), list(v[1])) for k, v in pares.items() if v}
    for k, p in holm({k: v["p"] for k, v in out.items()}).items():
        out[k]["p_holm"] = p
    return out


def _fmt(v: float) -> str:
    return "—" if v is None or math.isnan(v) else f"{v:.0%}" if abs(v) <= 1 else f"{v:.1f}"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("runs", nargs="+", help="diretórios de avaliação (glob; vários = seeds do mesmo sistema); o 1º é a referência")
    p.add_argument("--limiar-bacen", type=float, default=LIMIAR_BACEN)
    p.add_argument("--out", help="grava a comparação em JSON")
    args = p.parse_args()

    grupos = []
    for pat in args.runs:
        dirs = sorted(glob.glob(pat)) or [pat]
        grupos.append((Path(pat).name.replace("*", "★"), [load_preds(d) for d in dirs]))
    res = {nome: [compute(r, args.limiar_bacen) for r in runs] for nome, runs in grupos}

    primeiro = next(iter(res.values()))[0]
    print(f"\n{primeiro['n']} conversas de teste ({primeiro['bacen_n']} BACEN; com sub-assunto: "
          f"{primeiro['metricas'].get('sub_assunto_2_passos', {}).get('n', 0)}). Seed única: valor [IC 95%]. "
          "Várias seeds: média ± desvio entre seeds [menor IC inf., maior IC sup.].\n")
    w = 30
    print(f"{'métrica':26s}" + "".join(f"{n[:w - 2]:>{w}s}" for n in res))
    for k in primeiro["metricas"]:
        cells = []
        for runs in res.values():
            ms = [r["metricas"].get(k) for r in runs]
            if any(x is None for x in ms):
                cells.append("—")
                continue
            vals = [x["valor"] for x in ms]
            lo, hi = min(x["ic95"][0] for x in ms), max(x["ic95"][1] for x in ms)
            centro = _fmt(vals[0]) if len(vals) == 1 else f"{_fmt(statistics.mean(vals))}±{statistics.stdev(vals):.0%}"
            cells.append(f"{centro} [{_fmt(lo)}, {_fmt(hi)}]")
        print(f"{k:26s}" + "".join(f"{c:>{w}s}" for c in cells))

    ref_nome, ref_runs = grupos[0]
    comparacoes = {}
    for nome, runs in grupos[1:]:
        # Pareia a i-ésima seed de cada sistema; um sistema de execução única pareia com todas.
        k = max(len(ref_runs), len(runs))
        pares = [paired(ref_runs[i % len(ref_runs)], runs[i % len(runs)], args.limiar_bacen) for i in range(k)]
        comparacoes[nome] = pares
        print(f"\nMcNemar exato, {ref_nome} vs {nome} ({k} par(es) de execuções; p com correção de Holm entre métricas):")
        for met in pares[0]:
            difs = [x[met]["diferenca"] for x in pares]
            ps = [x[met]["p_holm"] for x in pares]
            ic = pares[0][met]["ic95"]
            print(f"  {met:24s} diferença {statistics.mean(difs):+.0%} (IC 95% do 1º par [{ic[0]:+.0%}, {ic[1]:+.0%}])"
                  f"  p_holm {'%.3g' % max(ps) if k == 1 else f'máx {max(ps):.3g}'}"
                  f"  discordantes {pares[0][met]['so_a_acerta']}/{pares[0][met]['so_b_acerta']}")
    if args.out:
        Path(args.out).write_text(json.dumps({"metricas": res, "mcnemar": comparacoes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
