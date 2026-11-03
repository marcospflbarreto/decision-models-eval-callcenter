"""Prompts para gerar uma conversa a partir de uma Spec."""

from __future__ import annotations

from .sampler import BANCO, Spec

SYSTEM = f"""Você escreve transcrições realistas de ligações de call center do {BANCO}, um banco brasileiro fictício.
Escreva em português do Brasil coloquial, como pessoas reais falam ao telefone.
Regras:
- Nunca mencione rótulos internos como "criticidade", "nível", "grave", "importante", "categoria" ou "assunto".
- O atendente não classifica a gravidade em voz alta; a gravidade deve transparecer pelos fatos (valores, prazos, prejuízo, histórico, ameaças).
- Só mencione Banco Central, Ouvidoria, Procon, Reclame Aqui ou Justiça se a especificação pedir.
- Use valores em reais, datas e números de protocolo plausíveis.
- Responda apenas com JSON válido no formato pedido."""

RUIDO = {
    "nenhum": "Transcrição limpa, com pontuação correta.",
    "leve": "Transcrição automática (ASR) com alguns erros: pontuação irregular, hesitações (ãh, né, tipo) e uma ou outra palavra trocada.",
    "forte": "Transcrição automática (ASR) ruim: quase sem pontuação, tudo em minúsculas, palavras trocadas por outras de som parecido, frases cortadas e trechos [inaudível].",
}


def build_messages(spec: Spec, sub_descricao: str, definicoes: dict[str, str]) -> list[dict]:
    niveis = list(definicoes)
    alvo = niveis.index(spec.criticidade)
    acima = "; ".join(definicoes[n] for n in niveis[alvo + 1 : alvo + 2])
    abaixo = "; ".join(definicoes[n] for n in niveis[alvo - 1 : alvo]) if alvo else ""
    extras = []
    if spec.assunto_secundario:
        extras.append(f"- No meio da ligação o cliente menciona brevemente outro assunto ({spec.assunto_secundario}), mas o foco principal continua sendo o assunto acima.")
    if spec.distrator_bacen:
        extras.append(f"- Detalhe de passagem, sem tom de reclamação: {spec.distrator_bacen}. O cliente NÃO está reclamando ao Banco Central.")
    if spec.risco_bacen:
        extras.append("- A conversa deve deixar claro o risco regulatório descrito no fato que define a gravidade.")

    user = f"""Escreva a transcrição de uma ligação com esta especificação:

- Assunto: {sub_descricao}
- Situação: {spec.cenario}
- Fato que define a gravidade do caso: {spec.gatilho}
- O caso deve ser inequivocamente deste tipo: {definicoes[spec.criticidade]}
{f'- NÃO inclua elementos que o tornariam mais sério ({acima}).' + chr(10) if acima else ''}{f'- Deixe claro que é mais sério do que: {abaixo}.' + chr(10) if abaixo else ''}- Cliente: {spec.nome_cliente}, de {spec.cidade}, perfil {spec.perfil_cliente}. Se o atendente pedir o CPF, o cliente informa {spec.cpf}.
- Atendente: {spec.nome_atendente}, perfil {spec.perfil_atendente}.
- Desfecho: {spec.desfecho}
- Aproximadamente {spec.turnos} turnos de fala no total, começando pela saudação do atendente.
- Estilo do texto: {RUIDO[spec.ruido_asr]}
{chr(10).join(extras)}

Formato de saída (JSON):
{{"turnos": [{{"falante": "atendente" | "cliente", "texto": "..."}}],
  "resumo_atendente": "anotação curta (1-3 frases) que o atendente registra no sistema ao final"}}"""
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
