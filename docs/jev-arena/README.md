# Jev Arena: resultados incorporados

Cópia dos resultados do projeto local `jev-open` (clone de [theaiautomators/jev-arena](https://github.com/theaiautomators/jev-arena), licença MIT, ver [LICENSE-jev-arena.txt](LICENSE-jev-arena.txt) e [THIRD_PARTY-jev-arena.md](THIRD_PARTY-jev-arena.md)), trazidos em 03/11/2026. A síntese em português está no relatório [`docs/index.html`](../index.html).

| Pasta | Conteúdo | Origem |
|---|---|---|
| `relatorios/` | Relatórios interativos: Arena Full v2 (13 perfis), ABCD (5 perfis) e os dois pilotos (call center bancário, guardrails de agentes) | `jev-open/results/` |
| `fontes/` | Textos originais dos resultados, análise, protocolo e ressalvas (inglês) | `jev-open/docs/` |
| `evidencias/` | Revisões da auditoria e JSONs de evidência pequenos | `jev-open/docs/evidence/` |
| `suites/` | Código das duas suítes piloto (não versionadas no jev-open) e o `results.json` de cada execução | `jev-open/arena/`, `scripts/`, `.arena/runs/` |

Os SHA-256 de `arena-full-v2.html` e `abcd-v1.html` batem com [relatorios/manifest.json](relatorios/manifest.json). Os pacotes ZIP de evidência (com predições sanitizadas) ficam no [release original](https://github.com/theaiautomators/jev-arena/releases/tag/video-results-2026-09). Os JSONs grandes (`full-v2-summary.json`, `abcd-v1-summary.json`, `video-task-analysis.json`, `abcd-retrieval-correction.json`) continuam só no `jev-open`.

As execuções piloto `20261009-104549-8cd4da` (call center bancário) e `20261012-011218-334a1c` (guardrails) rodaram **apenas o baseline uniforme**: validam o pipeline, não medem nenhum modelo.
