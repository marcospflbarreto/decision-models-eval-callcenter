"""Sorteia a especificação (cenário + rótulos) de cada conversa sintética.

Os rótulos vêm daqui, por construção: o LLM só escreve a conversa que
corresponde à especificação. Assim cada exemplo já nasce rotulado.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from faker import Faker

BANCO = "Banco Meridiano"  # fictício, para não imitar instituições reais
NIVEIS = ["normal", "importante", "grave", "BACEN"]

DISTRATORES_BACEN = [
    "cliente comenta que viu no site do Banco Central como funciona o Pix",
    "cliente menciona que consultou o Registrato do Banco Central para ver suas dívidas",
    "cliente pergunta se a taxa Selic do Banco Central influencia nos juros",
    "cliente cita uma notícia sobre o Banco Central e as novas regras do Pix",
]


@dataclass
class Spec:
    id: str
    assunto: str
    sub_assunto: str
    criticidade: str
    risco_bacen: bool
    cenario: str
    gatilho: str
    perfil_cliente: str
    perfil_atendente: str
    desfecho: str
    turnos: int
    ruido_asr: str
    assunto_secundario: str | None
    distrator_bacen: str | None
    nome_cliente: str
    nome_atendente: str
    cpf: str
    cidade: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_taxonomy(path: str | Path = "config/taxonomy.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _cenario(c: str | dict) -> dict:
    """Cenário na taxonomia: texto puro (vale para todos os níveis) ou {t: texto, n: [níveis]}."""
    return {"t": c, "n": NIVEIS} if isinstance(c, str) else c


def _weighted(rng: random.Random, weights: dict):
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def sample_spec(tax: dict, index: int, seed: int = 42) -> Spec:
    # Uma RNG por índice: a conversa i é sempre a mesma, o que permite retomar.
    rng = random.Random(f"{seed}-{index}")
    fake = Faker("pt_BR")
    fake.seed_instance(rng.randrange(2**32))

    assuntos = tax["assuntos"]
    crit = tax["criticidade"]
    div = tax["diversidade"]

    # Sorteia a criticidade primeiro e só depois um cenário compatível com ela,
    # para não pedir combinações incoerentes (ex.: golpe do Pix com criticidade "normal").
    criticidade = _weighted(rng, crit["distribuicao"])
    pool = {
        (a, s): [c for c in map(_cenario, sub["cenarios"]) if criticidade in c["n"]]
        for a, v in assuntos.items()
        for s, sub in v["sub_assuntos"].items()
    }
    pool = {k: v for k, v in pool.items() if v}
    assunto, sub = _weighted(rng, {k: assuntos[k[0]]["peso"] / len(assuntos[k[0]]["sub_assuntos"]) for k in pool})
    cenario = rng.choice(pool[(assunto, sub)])["t"]

    secundario = None
    if rng.random() < div["prob_assunto_secundario"]:
        outros = [(a, s) for a, v in assuntos.items() for s in v["sub_assuntos"] if s != sub]
        a2, s2 = rng.choice(outros)
        secundario = assuntos[a2]["sub_assuntos"][s2]["descricao"]

    distrator = None
    if criticidade != "BACEN" and rng.random() < div["prob_distrator_bacen"]:
        distrator = rng.choice(DISTRATORES_BACEN)

    lo, hi = div["tamanho"][rng.choice(list(div["tamanho"]))]
    return Spec(
        id=f"conv-{seed}-{index:06d}",
        assunto=assunto,
        sub_assunto=sub,
        criticidade=criticidade,
        risco_bacen=criticidade == "BACEN",
        cenario=cenario,
        gatilho=rng.choice(crit["gatilhos"][criticidade]),
        perfil_cliente=rng.choice(div["perfil_cliente"]),
        perfil_atendente=rng.choice(div["perfil_atendente"]),
        # Caso "normal" não termina com cliente insatisfeito, senão vira outro nível.
        desfecho=rng.choice([d for d in div["desfecho"] if criticidade != "normal" or "insatisfeito" not in d]),
        turnos=rng.randint(lo, hi),
        ruido_asr=_weighted(rng, div["ruido_asr"]),
        assunto_secundario=secundario,
        distrator_bacen=distrator,
        nome_cliente=fake.name(),
        nome_atendente=fake.first_name(),
        cpf=fake.cpf(),
        cidade=fake.city(),
    )
