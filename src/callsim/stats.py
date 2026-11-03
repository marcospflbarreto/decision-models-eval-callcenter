"""Estatística para a avaliação: intervalos de confiança e teste pareado entre modelos.

Sem dependências além da biblioteca padrão, para que cada número reportado tenha uma
fórmula auditável:
- Wilson para proporções (acurácia, recall, precisão): correto mesmo com n pequeno e p perto de 0 ou 1,
  onde o intervalo normal ("p ± 1,96·ep") sai do [0, 1].
- Bootstrap percentil para métricas que não são proporções simples (macro-F1, ECE).
- McNemar exato para comparar dois modelos nas MESMAS conversas, com a diferença de acurácia
  e seu intervalo (bootstrap pareado) como tamanho de efeito.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centro - meia), min(1.0, centro + meia))


def bootstrap(fn: Callable[[list[int]], float], n: int, b: int = 2000, seed: int = 0) -> tuple[float, float]:
    """IC 95% percentil de fn(índices) reamostrando os n itens com reposição."""
    rng = random.Random(seed)
    vals = sorted(v for _ in range(b) if not math.isnan(v := fn([rng.randrange(n) for _ in range(n)])))
    if not vals:
        return (math.nan, math.nan)
    return (vals[int(0.025 * (len(vals) - 1))], vals[int(0.975 * (len(vals) - 1))])


def mcnemar(a_ok: Sequence[bool], b_ok: Sequence[bool], b: int = 2000, seed: int = 0) -> dict:
    """McNemar exato (binomial nos pares discordantes) + diferença de acurácia A − B com IC pareado."""
    n = len(a_ok)
    so_a = sum(x and not y for x, y in zip(a_ok, b_ok))
    so_b = sum(y and not x for x, y in zip(a_ok, b_ok))
    m = so_a + so_b
    p = 1.0 if m == 0 else min(1.0, 2 * sum(math.comb(m, k) for k in range(min(so_a, so_b) + 1)) / 2**m)
    diff = (sum(a_ok) - sum(b_ok)) / n
    ic = bootstrap(lambda idx: sum(a_ok[i] - b_ok[i] for i in idx) / len(idx), n, b, seed)
    return {"so_a_acerta": so_a, "so_b_acerta": so_b, "p": p, "diferenca": diff, "ic95": ic}


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Correção de Holm-Bonferroni: várias métricas comparadas entre os mesmos dois modelos."""
    ordem = sorted(pvals, key=pvals.get)
    out, acum = {}, 0.0
    for i, k in enumerate(ordem):
        acum = max(acum, min(1.0, (len(ordem) - i) * pvals[k]))
        out[k] = acum
    return out


def macro_f1(y: Sequence, pred: Sequence, classes: Sequence | None = None) -> float:
    classes = classes or sorted(set(y))
    f1s = []
    for c in classes:
        tp = sum(a == c and b == c for a, b in zip(y, pred))
        fp = sum(a != c and b == c for a, b in zip(y, pred))
        fn = sum(a == c and b != c for a, b in zip(y, pred))
        if tp + fp + fn:
            f1s.append(2 * tp / (2 * tp + fp + fn))
    return sum(f1s) / len(f1s) if f1s else math.nan


def ece(conf: Sequence[float], correct: Sequence[bool], bins: int = 10) -> float:
    total, err = len(conf), 0.0
    for b in range(bins):
        idx = [i for i, c in enumerate(conf) if b / bins < c <= (b + 1) / bins or (b == 0 and c == 0)]
        if idx:
            acc = sum(correct[i] for i in idx) / len(idx)
            avg = sum(conf[i] for i in idx) / len(idx)
            err += len(idx) / total * abs(acc - avg)
    return err
