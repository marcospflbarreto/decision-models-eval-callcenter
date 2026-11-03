#!/usr/bin/env bash
# Mede throughput de geração por modelo/concorrência nos MESMOS cenários (índices fixos),
# para comparar velocidade e qualidade lado a lado. Uso: scripts/bench.sh "modelo:conc ..."
set -euo pipefail
BASE_URL=${BASE_URL:-http://localhost:11435/v1}
START=${START:-1000}; N=${N:-16}
mkdir -p data/bench
for cfg in ${1:-"qwen3.8:27b:8 gemma4:12b:8 qwen2.5:14b:8"}; do
  model=${cfg%:*}; conc=${cfg##*:}
  out="data/bench/${model//[:\/]/_}_c${conc}.jsonl"; rm -f "$out" "${out%.jsonl}.errors.jsonl"
  curl -s "$BASE_URL/chat/completions" -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"oi\"}],\"max_tokens\":1}" > /dev/null  # aquece/carrega
  t0=$(date +%s)
  uv run callsim-generate --base-url "$BASE_URL" --model "$model" --concurrency "$conc" --start "$START" --n "$N" --out "$out" > /dev/null 2>&1
  t1=$(date +%s)
  uv run python - "$out" $((t1 - t0)) "$model" "$conc" <<'PY'
import json, sys, pathlib
path, secs, model, conc = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
rs = [json.loads(l) for l in open(path)]
errs = pathlib.Path(path.replace(".jsonl", ".errors.jsonl"))
n_err = sum(1 for _ in errs.open()) if errs.exists() else 0
tok = sum(r["gen"]["usage"].get("completion_tokens", 0) for r in rs)
rate = len(rs) / secs * 3600
print(f"{model:14s} c={conc:2s} ok={len(rs):3d} err={n_err:2d} {secs:5d}s {tok/secs:6.1f} tok/s {rate:6.0f} conv/h -> 30k em {30000/rate/24:5.1f} dias", flush=True)
PY
done
