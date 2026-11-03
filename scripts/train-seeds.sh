#!/usr/bin/env bash
# Treina o Laya com várias seeds e avalia cada uma, para reportar média ± desvio entre execuções
# em vez de um número de uma execução só (Empirical Standards, Data Science: variação entre execuções).
#
# Uso: scripts/train-seeds.sh [splits] [seeds...]
#   scripts/train-seeds.sh data/splits 0 1 2 3 4
#   scripts/train-seeds.sh data/splits-cenario 0 1 2
# Cada treino leva ~80 min no M5 Max (MPS). Seeds já treinadas são puladas (retomável).
set -euo pipefail
cd "$(dirname "$0")/.."

SPLITS=${1:-data/splits}; shift || true
SEEDS=${*:-0 1 2 3 4}
NOME=$(basename "$SPLITS")
LAYA=data/laya-$NOME
EPOCHS=${EPOCHS:-4}
export PYTORCH_ENABLE_MPS_FALLBACK=1

uv run callsim-laya-data --splits "$SPLITS" --out "$LAYA"
mkdir -p logs

for s in $SEEDS; do
  OUT=models/laya-$NOME-s$s
  if [ ! -f "$OUT/train_report.json" ]; then
    echo "== seed $s -> $OUT"
    # Sem --eval: o teste não entra no treino nem em nenhuma decisão de treino (só no callsim-laya-eval).
    uv run laya-train --data "$LAYA/train.jsonl" --base convaiinnovations/laya-multilingual \
      --out "$OUT" --device mps --epochs "$EPOCHS" --micro-batch 8 --grad-accum 4 \
      --shuffle-options --seed "$s" > "logs/train-$NOME-s$s.log" 2>&1
    uv run python -c "
import json, sys
from callsim.meta import run_meta
json.dump(run_meta({'train': '$LAYA/train.jsonl'}, seed=$s, base='convaiinnovations/laya-multilingual',
                   epochs=$EPOCHS, micro_batch=8, grad_accum=4, device='mps'),
          open('$OUT/train_meta.json', 'w'), ensure_ascii=False, indent=2)"
  fi
  uv run callsim-laya-eval --model "$OUT" --test "$SPLITS/test.jsonl" > "logs/eval-$NOME-s$s.txt" 2>&1
done

uv run callsim-baseline --test "$SPLITS/test.jsonl" > /dev/null
uv run callsim-compare "logs/eval/$NOME-test/laya-$NOME-s*" "logs/eval/$NOME-test/tfidf-logreg" \
  --out "logs/compare-$NOME.json" | tee "logs/compare-$NOME.txt"
