"""Baseline simples: TF-IDF + regressão logística, com as mesmas perguntas e o mesmo fluxo em 2 passos.

Serve de piso para o Laya: se um modelo de palavras-chave também acerta quase tudo, o conjunto de
teste não distingue os modelos (o texto sintético entrega o rótulo por vocabulário), e o ganho do
Laya precisa ser medido em dados mais difíceis. Treina em train + calib do mesmo diretório do teste.

Uso:
    uv run callsim-baseline --test data/splits/test.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union

from .meta import run_meta
from .metrics import LIMIAR_BACEN, write_run
from .sampler import NIVEIS

NOME = "tfidf-logreg"


def clf(balanceado: bool = False):
    # Palavras (1-2 gramas) + caracteres (pega erros de ASR e variações de grafia).
    feats = make_union(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True),
    )
    return make_pipeline(feats, LogisticRegression(C=10, max_iter=2000, class_weight="balanced" if balanceado else None))


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--test", default="data/splits/test.jsonl")
    p.add_argument("--treino", help="diretório com train.jsonl e calib.jsonl (padrão: o do --test)")
    p.add_argument("--limiar-bacen", type=float, default=LIMIAR_BACEN)
    p.add_argument("--out-dir", default="logs/eval")
    args = p.parse_args()

    test = Path(args.test)
    treino = Path(args.treino) if args.treino else test.parent
    train = load(treino / "train.jsonl") + load(treino / "calib.jsonl")
    records = load(test)
    x = [r["transcricao"] for r in train]
    lab = [r["labels"] for r in train]

    m_assunto = clf().fit(x, [l["assunto"] for l in lab])
    m_crit = clf(balanceado=True).fit(x, [NIVEIS.index(l["criticidade"]) for l in lab])
    m_bacen = clf(balanceado=True).fit(x, [l["risco_bacen"] for l in lab])
    m_sub = {}
    for a in sorted({l["assunto"] for l in lab}):
        idx = [i for i, l in enumerate(lab) if l["assunto"] == a]
        subs = {lab[i]["sub_assunto"] for i in idx}
        m_sub[a] = clf().fit([x[i] for i in idx], [lab[i]["sub_assunto"] for i in idx]) if len(subs) > 1 else subs.pop()

    xt = [r["transcricao"] for r in records]
    t0 = time.perf_counter()
    pa, pc, pb = m_assunto.predict_proba(xt), m_crit.predict_proba(xt), m_bacen.predict_proba(xt)
    preds = []
    for i, r in enumerate(records):
        assunto = m_assunto.classes_[pa[i].argmax()]
        ms = m_sub[assunto]
        if isinstance(ms, str):
            sub, sub_conf = ms, 1.0
        else:
            ps = ms.predict_proba([xt[i]])[0]
            sub, sub_conf = ms.classes_[ps.argmax()], float(ps.max())
        crit_probs = [float(pc[i][list(m_crit.classes_).index(k)]) if k in m_crit.classes_ else 0.0 for k in range(len(NIVEIS))]
        preds.append({
            "id": r["id"],
            "true": {**r["labels"], "criticidade": NIVEIS.index(r["labels"]["criticidade"]) if r["labels"].get("criticidade") else None},
            "pred": {
                "assunto": str(assunto),
                "assunto_conf": float(pa[i].max()),
                "sub_assunto": str(sub),
                "sub_assunto_conf": sub_conf,
                "criticidade": max(range(len(NIVEIS)), key=crit_probs.__getitem__),
                "criticidade_conf": max(crit_probs),
                "criticidade_probs": crit_probs,
                "p_bacen": float(pb[i][list(m_bacen.classes_).index(True)]),
            },
        })
    ms_conv = (time.perf_counter() - t0) * 1000 / len(records)

    # Treinado em outro diretório (ex.: teste real com modelo do sintético): o nome diz de onde veio o treino.
    d = Path(args.out_dir) / f"{test.parent.name}-{test.stem}" / (NOME if treino == test.parent else f"{NOME}-{treino.name}")
    meta = run_meta({"test": test, "train": treino / "train.jsonl", "calib": treino / "calib.jsonl"},
                    modelo=NOME, n_treino=len(train), ms_por_conversa=ms_conv)
    res = write_run(d, preds, meta, args.limiar_bacen)
    print(f"{NOME}: treino {len(train)}, teste {len(records)}, {ms_conv:.2f} ms/conversa -> {d}")
    for k, v in res["metricas"].items():
        print(f"  {k:26s} {v['valor']:.0%} [{v['ic95'][0]:.0%}, {v['ic95'][1]:.0%}]" if v["valor"] == v["valor"] else f"  {k:26s} —")


if __name__ == "__main__":
    main()
