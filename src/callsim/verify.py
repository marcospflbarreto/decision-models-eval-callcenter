"""Verificação cega: um LLM juiz classifica cada conversa sem ver o rótulo.

Mede se o texto gerado realmente corresponde à especificação. Os veredictos
ficam num cache (um por conversa e versão da taxonomia), então a verificação
também é incremental. Uso:
    uv run callsim-verify --max-minutes 30
`callsim-dataset --filtrar` usa os veredictos para descartar conversas ambíguas.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from pathlib import Path

from tqdm import tqdm

from .llm import ChatClient
from .meta import append_run, ollama_digest, run_meta
from .sampler import NIVEIS, load_taxonomy


def build_judge_prompt(tax: dict, conversa: str) -> list[dict]:
    subs = "\n".join(
        f"- {s}: {d['descricao']}" for a in tax["assuntos"].values() for s, d in a["sub_assuntos"].items()
    )
    crit = "\n".join(f"- {k}: {v}" for k, v in tax["criticidade"]["definicoes"].items())
    user = f"""Classifique a ligação de call center bancário abaixo.

Sub-assuntos possíveis (escolha o assunto PRINCIPAL):
{subs}

Criticidade (escolha uma):
{crit}

Ligação:
\"\"\"
{conversa}
\"\"\"

Responda em JSON: {{"sub_assunto": "<chave>", "criticidade": "<normal|importante|grave|BACEN>"}}"""
    return [{"role": "user", "content": user}]


def load_verdicts(path: Path, versao: int) -> dict[str, dict]:
    """Veredictos da versão atual da taxonomia, por id de conversa."""
    if not path.exists():
        return {}
    out = {}
    for line in path.open(encoding="utf-8"):
        if line.strip() and (v := json.loads(line)).get("versao") == versao:
            out[v["id"]] = v
    return out


def agrees(labels: dict, verdict: dict) -> bool:
    """Critério para manter a conversa: mesmo sub-assunto, mesma decisão BACEN e criticidade a no máximo 1 nível."""
    crit = verdict.get("criticidade")
    if verdict.get("sub_assunto") != labels["sub_assunto"] or crit not in NIVEIS:
        return False
    if (crit == "BACEN") != labels["risco_bacen"]:
        return False
    return abs(NIVEIS.index(crit) - NIVEIS.index(labels["criticidade"])) <= 1


def report(records: list[dict], verdicts: dict[str, dict]) -> None:
    pairs = [(r["labels"], verdicts[r["id"]]) for r in records if r["id"] in verdicts]
    if not pairs:
        print("nenhum veredicto ainda")
        return
    n = len(pairs)
    sub_ok = sum(v.get("sub_assunto") == lab["sub_assunto"] for lab, v in pairs)
    crit_ok = sum(v.get("criticidade") == lab["criticidade"] for lab, v in pairs)
    bacen_true = [v.get("criticidade") == "BACEN" for lab, v in pairs if lab["risco_bacen"]]
    bacen_false = [v.get("criticidade") == "BACEN" for lab, v in pairs if not lab["risco_bacen"]]
    print(f"\n{n} conversas com veredicto")
    print(f"  sub_assunto concorda: {sub_ok / n:.0%}")
    print(f"  criticidade concorda: {crit_ok / n:.0%}")
    if bacen_true:
        print(f"  BACEN: juiz confirma {sum(bacen_true)}/{len(bacen_true)}; marca BACEN em {sum(bacen_false)} não-BACEN")
    print(f"  mantidas pelo filtro: {sum(agrees(lab, v) for lab, v in pairs) / n:.0%}")
    print("  criticidade rótulo -> juiz:", dict(sorted(Counter((lab["criticidade"], v.get("criticidade", "?")) for lab, v in pairs).items())))
    print("  sub_assunto rótulo -> juiz (top erros):", Counter((lab["sub_assunto"], v.get("sub_assunto")) for lab, v in pairs if v.get("sub_assunto") != lab["sub_assunto"]).most_common(5))


async def run(args: argparse.Namespace) -> None:
    tax = load_taxonomy(args.taxonomy)
    versao = tax.get("versao", 1)
    records = [json.loads(line) for line in Path(args.inp).open(encoding="utf-8") if line.strip()]
    cache = Path(args.verdicts)
    verdicts = load_verdicts(cache, versao)
    todo = [r for r in records if r["id"] not in verdicts]
    print(f"{len(verdicts)} já verificadas (taxonomia v{versao}); verificando {len(todo)} com {args.model}")

    append_run(cache.parent / "runs.jsonl", run_meta({"taxonomia": args.taxonomy}, etapa="verify", args=vars(args),
                                     modelo_digest=ollama_digest(args.base_url, args.model)))
    client = ChatClient(args.base_url, args.model)
    queue: asyncio.Queue[dict] = asyncio.Queue()
    for r in todo:
        queue.put_nowait(r)
    deadline = time.time() + args.max_minutes * 60 if args.max_minutes else float("inf")
    bar = tqdm(total=len(todo), unit="conv")

    with cache.open("a", encoding="utf-8") as f:

        async def worker() -> None:
            while not queue.empty() and time.time() < deadline:
                r = queue.get_nowait()
                try:
                    out, _ = await client.json_chat(build_judge_prompt(tax, r["transcricao"]), temperature=0, max_tokens=100)
                    v = {"id": r["id"], "versao": versao, "model": args.model,
                         "sub_assunto": out.get("sub_assunto"), "criticidade": out.get("criticidade")}
                    f.write(json.dumps(v, ensure_ascii=False) + "\n")
                    f.flush()
                    verdicts[r["id"]] = v
                except Exception:  # noqa: BLE001 - fica sem veredicto e é tentada na próxima execução
                    pass
                bar.update(1)

        await asyncio.gather(*(worker() for _ in range(args.concurrency)))
    bar.close()
    await client.aclose()
    report(records, verdicts)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inp", default="data/raw/conversations.jsonl")
    p.add_argument("--verdicts", default="data/raw/verdicts.jsonl", help="cache de veredictos")
    p.add_argument("--taxonomy", default="config/taxonomy.yaml")
    p.add_argument("--base-url", default="http://localhost:11435/v1")
    p.add_argument("--model", default="qwen3.8:27b")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--max-minutes", type=float, default=0, help="para após N minutos (0 = sem limite)")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
