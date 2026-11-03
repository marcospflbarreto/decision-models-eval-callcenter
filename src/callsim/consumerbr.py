"""Conjunto de teste com reclamações reais: ConsumerBR (texto) + Dados abertos do consumidor.gov.br (rótulos).

O ConsumerBR (Zenodo 10.5281/zenodo.18022568, uso restrito a pesquisa) traz o texto anonimizado das
reclamações, mas não o assunto. Os Dados abertos mensais (finalizadas_AAAA-MM.zip) trazem Assunto e
Problema, mas não o texto. Não há id comum: cada reclamação é casada pelos campos que as duas fontes
têm (empresa, cidade, UF, tempo de resposta, nota, avaliação) e pela data (finalização entre abertura +
tempo de resposta e 45 dias depois). Só entram casamentos únicos nos dois sentidos.

Os rótulos são os que o consumidor escolheu ao registrar a reclamação, traduzidos para a nossa
taxonomia por config/consumerbr_map.yaml. Criticidade e risco BACEN ficam nulos (a fonte não tem).

Grava em --out:
    todos.jsonl   todas as reclamações casadas e mapeadas
    test.jsonl    amostra estratificada (até --por-classe por assunto/sub-assunto), no formato dos splits
    runs.jsonl    metadados da execução

Uso:
    uv run callsim-consumerbr
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path

import yaml

from .meta import append_run, run_meta

JANELA_DIAS = 45


def _aval(s: str) -> str:
    s = s.strip().lower()
    return "res" if s.startswith("resolvid") else "nres" if s.startswith("não resolvid") else "na"


def _key(empresa: str, cidade: str, uf: str, tempo: str, nota: str, aval: str) -> tuple:
    return (empresa.strip(), cidade.strip().lower(), uf.strip(), tempo.strip(), nota.strip(), aval)


def load_dados_abertos(pasta: Path, segmento: str) -> list[dict]:
    rows = []
    for z in sorted(pasta.glob("finalizadas_*.zip")):
        with zipfile.ZipFile(z) as zf:
            raw = zf.read(zf.namelist()[0])
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        for r in csv.DictReader(io.StringIO(text, newline=""), delimiter=";"):
            r = {k.strip(): (v or "") for k, v in r.items() if k}
            if r.get("Segmento de Mercado") == segmento:
                rows.append(r)
    return rows


def _data(s: str) -> date:
    # Os arquivos mensais alternam entre AAAA-MM-DD e DD/MM/AAAA.
    s = s.strip()[:10]
    if "/" in s:
        d, m, y = map(int, s.split("/"))
        return date(y, m, d)
    return date.fromisoformat(s)


def map_labels(mapa: dict, assunto_orig: str, problema: str) -> tuple[str, str | None] | None:
    base = mapa["assuntos"].get(assunto_orig.strip())
    if base is None:
        return None
    hit = mapa["problemas"].get(base, {}).get(problema.strip())
    if hit:
        return hit[0], hit[1]
    return None if base == "cartao" else (base, None)


def _u(key: str) -> float:
    return int.from_bytes(hashlib.blake2b(key.encode(), digest_size=8).digest(), "big") / 2**64


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--consumerbr", default="data/external/consumerbr/ConsumerBR.csv")
    p.add_argument("--dados-abertos", default="data/external/consumidor-dados-abertos")
    p.add_argument("--map", default="config/consumerbr_map.yaml")
    p.add_argument("--out", default="data/consumerbr")
    p.add_argument("--por-classe", type=int, default=150, help="máximo por (assunto, sub-assunto) no test.jsonl")
    args = p.parse_args()

    mapa = yaml.safe_load(Path(args.map).read_text(encoding="utf-8"))
    da = load_dados_abertos(Path(args.dados_abertos), mapa["segmento"])
    idx: dict[tuple, list[int]] = collections.defaultdict(list)
    for i, r in enumerate(da):
        idx[_key(r["Nome Fantasia"], r["Cidade"], r["UF"], r["Tempo Resposta"], r["Nota do Consumidor"],
                 _aval(r["Avaliação Reclamação"]))].append(i)
    fim = [_data(r["Data Finalização"]) for r in da]
    empresas = {r["Nome Fantasia"].strip() for r in da}
    print(f"Dados abertos: {len(da)} reclamações do segmento, {len(empresas)} empresas, "
          f"finalização {min(fim)} a {max(fim)}", flush=True)

    csv.field_size_limit(10**9)
    cont = collections.Counter()
    casados: list[tuple[dict, int]] = []
    usos = collections.Counter()
    with open(args.consumerbr, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["empresa"].strip() not in empresas:
                continue
            cont["consumerbr_segmento"] += 1
            if not r["data_abertura"] or not r["reclamacao_labeled"].strip():
                continue
            ab = _data(r["data_abertura"])
            t = re.search(r"\((\d+) dia", r["data_resposta"] or "")
            t = t.group(1) if t else ""
            cid, _, uf = r["localizacao"].rpartition(" - ")
            nota = re.sub(r"\D", "", r["avaliacao_nota"] or "")
            lo = ab + timedelta(days=int(t or 0))
            cands = [i for i in idx.get(_key(r["empresa"], cid, uf, t, nota, _aval(r["status"])), [])
                     if lo <= fim[i] <= lo + timedelta(days=JANELA_DIAS)]
            if len(cands) == 1:
                casados.append((r, cands[0]))
                usos[cands[0]] += 1
            cont["sem_par" if not cands else "unico" if len(cands) == 1 else "ambiguo"] += 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    registros = []
    origem = collections.Counter()
    for r, i in casados:
        if usos[i] > 1:  # a mesma linha dos Dados abertos casou com mais de uma reclamação
            cont["descartado_par_repetido"] += 1
            continue
        lab = map_labels(mapa, da[i]["Assunto"], da[i]["Problema"])
        if lab is None:
            cont["fora_da_taxonomia"] += 1
            origem[da[i]["Assunto"]] += 1
            continue
        registros.append({
            "id": f"cbr-{r['ID'][:16]}",
            "labels": {"assunto": lab[0], "sub_assunto": lab[1], "criticidade": None, "risco_bacen": None},
            # A reclamação é a fala do cliente; o prefixo segue o formato das transcrições sintéticas.
            "transcricao": "Cliente: " + r["reclamacao_labeled"].strip(),
            "fonte": {"consumerbr_id": r["ID"], "empresa": r["empresa"], "data_abertura": r["data_abertura"],
                      "assunto_orig": da[i]["Assunto"], "grupo_problema_orig": da[i]["Grupo Problema"],
                      "problema_orig": da[i]["Problema"]},
        })
    cont["mapeados"] = len(registros)

    with (out / "todos.jsonl").open("w", encoding="utf-8") as fh:
        for rec in registros:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # Amostra estratificada e determinística: as --por-classe de menor hash em cada (assunto, sub).
    grupos = collections.defaultdict(list)
    for rec in registros:
        grupos[(rec["labels"]["assunto"], rec["labels"]["sub_assunto"] or "")].append(rec)
    teste = []
    for g in sorted(grupos):
        teste += sorted(grupos[g], key=lambda rec: _u(rec["id"]))[: args.por_classe]
    with (out / "test.jsonl").open("w", encoding="utf-8") as fh:
        for rec in teste:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(json.dumps(cont, ensure_ascii=False, indent=1))
    print("fora da taxonomia (assunto de origem):", origem.most_common(6))
    print(f"\n{'assunto':28s}{'sub_assunto':24s}{'todos':>8s}{'teste':>7s}")
    for (a, s), recs in sorted(grupos.items()):
        print(f"{a:28s}{s or '(sem sub)':24s}{len(recs):8d}{min(len(recs), args.por_classe):7d}")
    print(f"-> {out}/todos.jsonl ({len(registros)}), {out}/test.jsonl ({len(teste)})")
    append_run(out / "runs.jsonl", run_meta(
        {"consumerbr": args.consumerbr, "mapa": args.map,
         **{f"da_{z.stem}": z for z in sorted(Path(args.dados_abertos).glob("finalizadas_*.zip"))}},
        etapa="consumerbr", args=vars(args), contagens=dict(cont)))


if __name__ == "__main__":
    main()
