# Decision models: call center bancário sintético

Gera conversas sintéticas **já rotuladas** de um call center bancário, para treinar e avaliar
decision models (Laya) contra o benchmark Jev.

Cada conversa tem quatro rótulos:

| Pergunta (Laya) | Tipo | Valores |
|---|---|---|
| `assunto` | `choice` | cartoes_limite, faturas_cobranca, conta_pix, emprestimos_financiamentos |
| `sub_assunto` | `choice` (2ª etapa, por assunto) | 13 sub-assuntos, ver [config/taxonomy.yaml](config/taxonomy.yaml) |
| `criticidade` | `score` | normal < importante < grave < BACEN |
| `risco_bacen` | `noul` | true/false (true ⇔ criticidade = BACEN) |

## Como funciona

1. [sampler.py](src/callsim/sampler.py) sorteia uma especificação por conversa (sub-assunto, criticidade-alvo,
   gatilho de gravidade, perfil do cliente e do atendente, desfecho, tamanho, ruído de ASR, assunto secundário,
   distrator "Banco Central" sem reclamação). **Os rótulos vêm da especificação**, por construção.
2. [generate.py](src/callsim/generate.py) pede a um LLM (qualquer endpoint OpenAI-compatível: Ollama, vLLM, gateway de cloud)
   que escreva a transcrição e o resumo do atendente; valida o formato e rejeita vazamento de rótulo.
3. [dataset.py](src/callsim/dataset.py) remove quase-duplicatas (MinHash) e divide em `train/calib/test` estratificado.

Dados pessoais (nomes, CPFs, cidades) são **fictícios** (Faker pt_BR) e o banco é o fictício "Banco Meridiano".

## Uso

```bash
uv sync
ollama pull gemma4:12b && ollama pull qwen3.8:27b               # gerador e juiz
scripts/ollama-fast.sh                                       # outro terminal: Ollama otimizado na porta 11435
uv run callsim-generate --n 30000                            # retomável; gemma4:12b, 8 em paralelo
uv run callsim-verify                                        # juiz cego; incremental (cache em data/raw/verdicts.jsonl)
uv run callsim-dataset --filtrar                             # dedup + filtro do juiz + splits
```

`callsim-verify` é a verificação cega: um juiz (qwen3.8:27b) classifica cada conversa sem ver o rótulo.
`--filtrar` mantém só as conversas em que o juiz concorda no sub-assunto, na decisão BACEN e na criticidade
(a no máximo 1 nível). Os veredictos são guardados por versão da taxonomia (`versao` em
[config/taxonomy.yaml](config/taxonomy.yaml)): ao mudar definições, aumente a versão e rode `callsim-verify` de novo.

**Geração incremental:** `uv run callsim-generate --n 30000 --max-minutes 60` gera durante 1 hora e para.
Rodar o mesmo comando de novo continua do ponto em que parou (as conversas são deterministas por índice e as já
geradas são puladas; falhas são tentadas de novo). Para ir além de 30k, aumente `--n`. O split de cada conversa
é fixo (hash do id), então regenerar os splits depois de novas rodadas nunca move conversas do teste para o treino.

Para outro backend: `--base-url http://host:8000/v1 --model <nome>` (e `LLM_API_KEY` se precisar).
Para dividir entre máquinas: `--start 0 --n 15000` numa e `--start 15000 --n 15000` na outra.

## Avaliação (alinhada aos ACM SIGSOFT Empirical Standards)

```bash
uv run callsim-dataset --filtrar                                    # split por id (+ test_nao_filtrado.jsonl)
uv run callsim-dataset --filtrar --split-por cenario --out data/splits-cenario   # cenários inteiros só no teste
uv run callsim-baseline --test data/splits/test.jsonl               # piso: TF-IDF + regressão logística
uv run callsim-laya-eval --model models/laya-callcenter-v1          # predições por item + IC 95%
scripts/train-seeds.sh data/splits 0 1 2 3 4                       # 5 seeds (~80 min cada), avalia e compara
uv run callsim-compare 'logs/eval/splits-test/laya-splits-s*' logs/eval/splits-test/tfidf-logreg
```

- **Três conjuntos de teste**:
  - `splits/test` usa as mesmas situações do treino.
  - `splits/test_nao_filtrado` não passa pelo filtro do juiz, que removeria os casos ambíguos e deixaria o teste mais fácil.
  - `splits-cenario/test` reúne um cenário por sub-assunto que nunca aparece no treino e mede a generalização. Um modelo treinado em `data/splits` **não** pode ser avaliado em `splits-cenario/test`, porque esses cenários estão no treino dele. Use `scripts/train-seeds.sh data/splits-cenario`.
- **Predições brutas**: cada avaliação grava `logs/eval/<conjunto>/<modelo>/preds.jsonl` (uma linha por conversa) e `metrics.json` (métricas e metadados). Qualquer modelo novo, inclusive o Jev, entra gravando o mesmo formato de `preds.jsonl`.
- **Intervalos**:
  - Wilson para proporções.
  - Bootstrap para macro-F1 e ECE.
  - McNemar exato pareado, com correção de Holm entre métricas, e a diferença de acurácia como tamanho de efeito.
  - Com várias seeds, a comparação mostra média ± desvio entre execuções.
- **Rastreabilidade**: `data/raw/runs.jsonl`, `data/splits*/runs.jsonl`, `models/*/train_meta.json` e `metrics.json` guardam:
  - commit do git, `uv.lock` e versões das bibliotecas;
  - digest do modelo no Ollama;
  - hashes SHA-256 dos arquivos de dados usados.

## Teste com reclamações reais (ConsumerBR)

O teste sintético só mede se o modelo aprendeu a distribuição sintética. Para medir em texto real, usamos o
[ConsumerBR](https://zenodo.org/records/18022568) (3,1 milhões de reclamações do consumidor.gov.br, mai/2021 a
abr/2025, texto anonimizado). **Os termos permitem só uso em pesquisa**: sem reidentificação nem redistribuição. Os dados
ficam em `data/external` e não vão para o git.

O ConsumerBR não traz o assunto. Por isso [consumerbr.py](src/callsim/consumerbr.py) casa cada reclamação com
os [Dados abertos](https://www.consumidor.gov.br/pages/dadosabertos/externo/) mensais, que têm Assunto e Problema
mas não o texto. Não há id comum: o casamento usa empresa, cidade, UF, tempo de resposta, nota, avaliação e
janela de datas, e só aceita pares únicos. [config/consumerbr_map.yaml](config/consumerbr_map.yaml)
traduz os rótulos para a nossa taxonomia.

```bash
# data/external/consumerbr/ConsumerBR.csv (Zenodo) e data/external/consumidor-dados-abertos/finalizadas_*.zip
uv run callsim-consumerbr                                            # -> data/consumerbr/{todos,test}.jsonl
uv run callsim-laya-eval --model models/laya-callcenter-v1 --test data/consumerbr/test.jsonl
uv run callsim-baseline --test data/consumerbr/test.jsonl --treino data/splits
```

Limites desse teste:

- O rótulo é **prata**: foi escolhido pelo consumidor no formulário, não por um anotador.
- Só o assunto é sempre conhecido. O sub-assunto aparece quando o Problema aponta para um único sub nosso.
- Criticidade e risco BACEN não existem na fonte, e as métricas que dependem deles ficam de fora.
- O texto é uma reclamação escrita, não a transcrição de uma ligação: o teste mede também a mudança de domínio.

**Auditoria cega.** 200 dessas reclamações (estratificadas, embaralhadas, sem o rótulo prata) são rotuladas
à mão na página "Auditoria ConsumerBR". Cada pessoa vê só as próprias respostas. A chave com o rótulo prata
fica em `data/consumerbr/auditoria/amostra.jsonl`. Depois de exportar a coleção `anotacoes` da página para
`data/consumerbr/auditoria/export`:

```bash
uv run python -m callsim.auditoria       # ruído do rótulo prata, kappa entre anotadores, gold.jsonl
uv run callsim-laya-eval --model models/laya-callcenter-v1 --test data/consumerbr/auditoria/gold.jsonl
```

O `gold.jsonl` é o primeiro teste real com criticidade e risco BACEN.

**Rotulagem por LLM.** Sem anotadores com conhecimento de ouvidoria, [rotular_llm.py](src/callsim/rotular_llm.py)
aplica o mesmo protocolo da página com dois LLMs abertos, rodando localmente (o texto não sai da máquina).
Os modelos são de famílias diferentes do gerador (gemma) e do juiz (qwen), porque o treino foi gerado e
filtrado por esses dois. Onde os dois LLMs concordam, o rótulo entra no gold; as divergências vão para
adjudicação humana. No estudo, isso aparece como "rotulado por LLMs com adjudicação humana", não como gold humano.

```bash
ollama pull mistral-small3.1:24b && ollama pull llama3.3:70b
uv run python -m callsim.rotular_llm --model mistral-small3.1:24b
uv run python -m callsim.rotular_llm --model llama3.3:70b
uv run python -m callsim.auditoria --export data/consumerbr/auditoria/export_llm --out data/consumerbr/auditoria/gold_llm.jsonl
```

## Custo de geração

~1.000 tokens de saída por conversa → 30k conversas ≈ 30M tokens. Benchmark no M5 Max (64 GB),
[scripts/ollama-fast.sh](scripts/ollama-fast.sh) com contexto de 8k, KV cache q8_0 e flash attention,
mesmos cenários, juiz cego qwen3.8:27b:

| Modelo | Paralelo | tok/s | 30k conversas | Sub-assunto ok | Criticidade ok (±1) |
|---|---|---|---|---|---|
| Ollama padrão, qwen3.8:27b | 4 | 23 | ~15 dias | — | — |
| qwen3.8:27b | 8 | 36 | 8,5 dias | 100% | 50% (75%) |
| qwen2.5:14b | 8 | 106 | 2,5 dias | 94% | 50% (69%) |
| **gemma4:12b** | 8 | 88–128 | **~3 dias** | 94% | 56% (88%) |
| gemma4:12b + cenários restritos + prompt com níveis | 8 | 112 | ~3 dias | 94% | **84% (100%)** |
| idem | 16 | 120 | 2,8 dias | — | — |

A baixa concordância inicial vinha de combinações incoerentes (ex.: golpe do Pix com criticidade "normal"),
não do modelo. Por isso cada cenário em [config/taxonomy.yaml](config/taxonomy.yaml) declara em quais níveis faz sentido (`n:`),
e o prompt explica o nível-alvo e o que o separa dos vizinhos. Amostras pequenas (16–32 conversas): números indicativos.

## Limitações

- Rótulos por construção podem não bater com o texto que o LLM escreveu (ex.: uma "dúvida sobre fatura" que vira
  cobrança errada). Uma verificação cega por outro modelo é recomendada antes do treino.
- O conjunto de teste sintético mede se o modelo aprendeu a distribuição sintética; o benchmark que vale contra o Jev
  precisa de um conjunto gold com conversas reais (anonimizadas).
