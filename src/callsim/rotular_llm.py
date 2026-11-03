"""Rotula as 200 reclamações da auditoria com um LLM local, no lugar de um anotador humano.

Usa o mesmo protocolo da página "Auditoria ConsumerBR" (definições do taxonomy.yaml, opção "fora da
taxonomia", regra do BACEN) e grava a resposta no formato exportado da página, para que
`python -m callsim.auditoria --export <pasta>` trate cada modelo como um anotador.

Não use o gerador (gemma) nem o juiz (qwen) como anotadores: o treino foi gerado e filtrado por eles,
e o teste passaria a medir concordância com esses modelos.

Uso (o texto não sai da máquina):
    uv run python -m callsim.rotular_llm --model mistral-small3.1:24b
    uv run python -m callsim.rotular_llm --model llama3.3:70b
    uv run python -m callsim.auditoria --export data/consumerbr/auditoria/export_llm --out data/consumerbr/auditoria/gold_llm.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from tqdm import tqdm

from .llm import ChatClient
from .meta import ollama_digest, run_meta
from .sampler import NIVEIS


def build_prompt(tax: dict, texto: str) -> list[dict]:
    subs = "\n".join(
        f"  - {s}: {d}" for a, v in tax["assuntos"].items() for s, d in v["subs"].items()
    )
    assuntos = "\n".join(f"- {a}: {v['descricao']}" for a, v in tax["assuntos"].items())
    por_assunto = "\n".join(f"- {a}: {', '.join(v['subs'])}" for a, v in tax["assuntos"].items())
    crit = "\n".join(f"- {k}: {v}" for k, v in tax["criticidade"].items())
    system = f"""Você é um analista de ouvidoria de um banco brasileiro. Classifique reclamações de clientes.

Assuntos:
{assuntos}
- fora: a reclamação não se encaixa em nenhum assunto acima (ex.: seguro, investimento, atendimento em geral).

Sub-assuntos de cada assunto:
{por_assunto}

Definição dos sub-assuntos:
{subs}
Se o assunto estiver certo mas nenhum sub-assunto se aplicar, use "nenhum".

Criticidade (escolha uma):
{crit}

Regras:
- Escolha o assunto PRINCIPAL, o motivo central da reclamação.
- Toda reclamação veio do site consumidor.gov.br. Isso, sozinho, NÃO é BACEN: só é BACEN se o texto citar
  Banco Central, Ouvidoria, Procon ou Justiça (já acionados ou ameaça explícita), ou mostrar o banco negando
  um direito regulatório.
- Trechos [MASCARADO] são dados anonimizados; ignore-os.
- "duvida" = true se você não tem segurança na classificação.

Responda só em JSON:
{{"justificativa": "<1 ou 2 frases>", "assunto": "<chave ou fora>", "sub_assunto": "<chave ou nenhum>",
"criticidade": "<normal|importante|grave|BACEN>", "duvida": <true|false>}}"""
    return [{"role": "system", "content": system}, {"role": "user", "content": f'Reclamação:\n"""\n{texto}\n"""'}]


def valida(tax: dict, out: dict) -> dict:
    assunto, sub, crit = out.get("assunto"), out.get("sub_assunto"), out.get("criticidade")
    if assunto != "fora" and assunto not in tax["assuntos"]:
        raise ValueError(f"assunto inválido: {assunto!r}")
    if assunto == "fora":
        sub = "fora"
    elif sub not in tax["assuntos"][assunto]["subs"]:
        sub = "nenhum"  # sub de outro assunto ou inexistente: o assunto manda
    if crit not in NIVEIS:
        raise ValueError(f"criticidade inválida: {crit!r}")
    return {"assunto": assunto, "sub": sub, "crit": crit, "bacen": crit == "BACEN",
            "duvida": bool(out.get("duvida")), "obs": str(out.get("justificativa", "")).strip()}


async def run(args: argparse.Namespace) -> None:
    tax = json.loads(Path(args.taxonomia).read_text(encoding="utf-8"))
    amostra = [json.loads(l) for l in open(args.amostra, encoding="utf-8")][: args.limite]
    slug = re.sub(r"[^a-z0-9.]+", "-", args.model.lower()).strip("-")
    out_path = Path(args.out) / f"{slug}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {"id": slug, "itens": {}}
    feitos = set(doc["itens"])
    pend = [r for r in amostra if r["item"] not in feitos]

    client = ChatClient(args.base_url, args.model, reasoning=False)
    erros = []
    for r in tqdm(pend, desc=slug):
        texto = r["transcricao"].removeprefix("Cliente: ")
        for tentativa in range(3):
            try:
                out, _ = await client.json_chat(build_prompt(tax, texto), temperature=0, max_tokens=600)
                doc["itens"][r["item"]] = valida(tax, out)
                break
            except Exception as e:  # noqa: BLE001 - JSON ou rótulo inválido: tenta de novo
                if tentativa == 2:
                    erros.append((r["item"], str(e)[:200]))
        # grava a cada item: dá para interromper e retomar
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    await client.aclose()

    doc["meta"] = run_meta({"amostra": args.amostra, "taxonomia": args.taxonomia}, modelo=args.model,
                           digest=ollama_digest(args.base_url, args.model), temperatura=0)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {out_path}: {len(doc['itens'])} itens; {len(erros)} falhas {erros[:5]}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", required=True)
    p.add_argument("--base-url", default="http://localhost:11434/v1")
    p.add_argument("--amostra", default="data/consumerbr/auditoria/amostra.jsonl")
    p.add_argument("--taxonomia", default="data/consumerbr/auditoria/taxonomia.json")
    p.add_argument("--out", default="data/consumerbr/auditoria/export_llm")
    p.add_argument("--limite", type=int, default=None, help="só os N primeiros itens (teste)")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
