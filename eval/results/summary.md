# Resultados do eval de retrieval

Gerado por `make eval` em 2026-11-19 (commit `2c1b983`), device `cpu` (13th Gen Intel(R) Core(TM) i5-13420H, 8 threads, torch 2.15.0+cu132). Vault sintético de `eval/vault` (80 notas), 60 perguntas (50 com resposta, 10 sem). `minilm-whole-title` é a config de produção.

## Geral (50 perguntas com resposta)

| config | R@1 | R@3 | R@5 | MRR | nDCG@5 | FP@0.4 | R@5 com t=0.4 | t sugerido (R@5 / FP) | p50 ms | p95 ms | indexação s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **minilm-whole-title** | 0.700 | 0.860 | 0.880 | 0.779 | 0.775 | 20% | 0.740 | 0.50 (0.600 / 10%) | 14.6 | 26.0 | 4.8 |
| minilm-whole-notitle | 0.660 | 0.860 | 0.920 | 0.766 | 0.793 | 20% | 0.800 | 0.45 (0.720 / 10%) | 11.8 | 15.6 | 3.6 |
| minilm-chunk-title | 0.720 | 0.820 | 0.940 | 0.799 | 0.819 | 40% | 0.840 | 0.55 (0.740 / 10%) | 14.7 | 16.5 | 14.4 |
| minilm-chunk-notitle | 0.720 | 0.880 | 0.960 | 0.812 | 0.817 | 40% | 0.900 | 0.60 (0.500 / 0%) | 14.4 | 16.8 | 12.8 |
| e5-small-whole-title | 0.700 | 0.840 | 0.880 | 0.775 | 0.784 | 100% | 0.880 | 0.90 (0.240 / 0%) | 14.8 | 16.8 | 8.2 |
| e5-small-whole-notitle | 0.680 | 0.840 | 0.860 | 0.767 | 0.764 | 100% | 0.860 | 0.90 (0.260 / 0%) | 14.8 | 16.4 | 7.9 |
| e5-small-chunk-title | 0.700 | 0.800 | 0.840 | 0.764 | 0.760 | 100% | 0.840 | 0.90 (0.400 / 0%) | 15.2 | 17.2 | 13.1 |
| e5-small-chunk-notitle | 0.760 | 0.840 | 0.880 | 0.812 | 0.813 | 100% | 0.880 | 0.90 (0.360 / 0%) | 14.9 | 16.8 | 12.2 |
| bge-m3-whole-title | 0.820 | 0.860 | 0.900 | 0.854 | 0.837 | 80% | 0.900 | 0.55 (0.700 / 10%) | 85.9 | 111.4 | 118.4 |
| bge-m3-whole-notitle | 0.800 | 0.880 | 0.920 | 0.851 | 0.827 | 80% | 0.920 | 0.55 (0.720 / 0%) | 80.5 | 105.5 | 115.4 |
| bge-m3-chunk-title | 0.820 | 0.900 | 0.900 | 0.870 | 0.856 | 90% | 0.900 | 0.60 (0.680 / 0%) | 85.5 | 107.1 | 141.5 |
| bge-m3-chunk-notitle | 0.800 | 0.900 | 0.900 | 0.855 | 0.852 | 90% | 0.900 | 0.55 (0.800 / 10%) | 82.5 | 108.4 | 133.3 |

## Recall@5 por kind e nas perguntas de cauda

Cauda = as 12 perguntas cuja resposta só aparece depois de ~400 palavras numa nota longa. A última coluna conta quantas notas passam do `max_seq_length` do modelo (o excesso é cortado sem aviso no modo nota inteira).

| config | literal | paraphrase | cross_lingual | cauda | max_seq_length | notas truncadas |
|---|---|---|---|---|---|---|
| minilm-whole-title | 0.960 | 0.733 | 0.900 | 0.750 | 128 | 80 |
| minilm-whole-notitle | 1.000 | 0.800 | 0.900 | 0.833 | 128 | 80 |
| minilm-chunk-title | 1.000 | 0.867 | 0.900 | 1.000 | 128 | 0 |
| minilm-chunk-notitle | 1.000 | 0.867 | 1.000 | 1.000 | 128 | 0 |
| e5-small-whole-title | 1.000 | 0.600 | 1.000 | 0.833 | 512 | 30 |
| e5-small-whole-notitle | 1.000 | 0.533 | 1.000 | 0.833 | 512 | 30 |
| e5-small-chunk-title | 1.000 | 0.533 | 0.900 | 0.917 | 512 | 0 |
| e5-small-chunk-notitle | 1.000 | 0.600 | 1.000 | 0.833 | 512 | 0 |
| bge-m3-whole-title | 1.000 | 0.667 | 1.000 | 0.917 | 8192 | 0 |
| bge-m3-whole-notitle | 1.000 | 0.733 | 1.000 | 0.917 | 8192 | 0 |
| bge-m3-chunk-title | 1.000 | 0.667 | 1.000 | 0.917 | 8192 | 0 |
| bge-m3-chunk-notitle | 1.000 | 0.667 | 1.000 | 0.917 | 8192 | 0 |

## Expansão pelo campo related (bge-m3-chunk-title)

Notas relacionadas às top-3 entram com score max(próprio, λ × score da origem) e a lista é reordenada.

| variante | R@5 | nDCG@5 | MRR | R@5 cauda |
|---|---|---|---|---|
| sem expansão | 0.900 | 0.856 | 0.870 | 0.917 |
| λ = 0.8 | 0.900 | 0.863 | 0.870 | 0.917 |
| λ = 0.9 | 0.900 | 0.879 | 0.870 | 0.917 |
| λ = 1.0 | 0.940 | 0.888 | 0.866 | 1.000 |
