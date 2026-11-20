# Resultados do eval de retrieval

Gerado por `make eval` em 2026-11-19 (commit `a91aac4`), device `cpu` (13th Gen Intel(R) Core(TM) i5-13420H, 8 threads, torch 2.15.0+cu132). Vault sintético de `eval/vault` (80 notas), 60 perguntas (50 com resposta, 10 sem). A config de produção (a que o `embed.py` usa) é **`minilm-chunk-title`**, em negrito nas tabelas, com corte em 0.55 (`DENNOU_SCORE_THRESHOLD`).

## Geral (50 perguntas com resposta)

| config | R@1 | R@3 | R@5 | MRR | nDCG@5 | FP@0.55 | R@5 com t=0.55 | t sugerido (R@5 / FP) | p50 ms | p95 ms | indexação s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| minilm-whole-title | 0.700 | 0.860 | 0.880 | 0.779 | 0.775 | 0% | 0.540 | 0.50 (0.600 / 10%) | 14.1 | 25.6 | 3.4 |
| minilm-whole-notitle | 0.660 | 0.860 | 0.920 | 0.766 | 0.793 | 0% | 0.380 | 0.45 (0.720 / 10%) | 13.8 | 16.3 | 3.3 |
| **minilm-chunk-title** | 0.720 | 0.820 | 0.960 | 0.802 | 0.832 | 10% | 0.740 | 0.55 (0.740 / 10%) | 10.8 | 14.5 | 13.4 |
| minilm-chunk-notitle | 0.700 | 0.860 | 0.960 | 0.799 | 0.813 | 20% | 0.720 | 0.60 (0.480 / 0%) | 11.3 | 27.9 | 11.7 |
| e5-small-whole-title | 0.720 | 0.840 | 0.860 | 0.780 | 0.769 | 100% | 0.860 | 0.90 (0.260 / 0%) | 14.5 | 32.0 | 19.7 |
| e5-small-whole-notitle | 0.700 | 0.840 | 0.880 | 0.777 | 0.765 | 100% | 0.880 | 0.90 (0.280 / 0%) | 14.8 | 17.2 | 7.5 |
| e5-small-chunk-title | 0.740 | 0.880 | 0.900 | 0.821 | 0.808 | 100% | 0.900 | 0.90 (0.400 / 0%) | 14.5 | 16.9 | 11.4 |
| e5-small-chunk-notitle | 0.800 | 0.860 | 0.900 | 0.843 | 0.831 | 100% | 0.900 | 0.90 (0.380 / 0%) | 13.1 | 16.2 | 10.7 |
| bge-m3-whole-title | 0.820 | 0.880 | 0.900 | 0.859 | 0.839 | 0% | 0.700 | 0.55 (0.700 / 0%) | 80.8 | 101.8 | 108.4 |
| bge-m3-whole-notitle | 0.820 | 0.900 | 0.900 | 0.859 | 0.825 | 0% | 0.720 | 0.55 (0.720 / 0%) | 84.8 | 108.0 | 107.3 |
| bge-m3-chunk-title | 0.820 | 0.900 | 0.900 | 0.862 | 0.849 | 20% | 0.780 | 0.60 (0.680 / 0%) | 79.9 | 99.9 | 123.7 |
| bge-m3-chunk-notitle | 0.840 | 0.900 | 0.920 | 0.873 | 0.850 | 10% | 0.800 | 0.55 (0.800 / 10%) | 79.6 | 103.4 | 116.3 |

## Recall@5 por kind e nas perguntas de cauda

Cauda = as 12 perguntas cuja resposta só aparece depois de ~400 palavras numa nota longa. A última coluna conta quantas notas passam do `max_seq_length` do modelo (o excesso é cortado sem aviso no modo nota inteira).

| config | literal | paraphrase | cross_lingual | cauda | max_seq_length | notas truncadas |
|---|---|---|---|---|---|---|
| minilm-whole-title | 0.960 | 0.733 | 0.900 | 0.750 | 128 | 80 |
| minilm-whole-notitle | 1.000 | 0.800 | 0.900 | 0.833 | 128 | 80 |
| **minilm-chunk-title** | 1.000 | 0.867 | 1.000 | 1.000 | 128 | 0 |
| minilm-chunk-notitle | 1.000 | 0.867 | 1.000 | 1.000 | 128 | 0 |
| e5-small-whole-title | 1.000 | 0.533 | 1.000 | 0.833 | 512 | 30 |
| e5-small-whole-notitle | 1.000 | 0.600 | 1.000 | 0.833 | 512 | 29 |
| e5-small-chunk-title | 1.000 | 0.667 | 1.000 | 0.917 | 512 | 0 |
| e5-small-chunk-notitle | 1.000 | 0.667 | 1.000 | 0.917 | 512 | 0 |
| bge-m3-whole-title | 1.000 | 0.667 | 1.000 | 0.917 | 8192 | 0 |
| bge-m3-whole-notitle | 1.000 | 0.667 | 1.000 | 0.917 | 8192 | 0 |
| bge-m3-chunk-title | 1.000 | 0.667 | 1.000 | 0.917 | 8192 | 0 |
| bge-m3-chunk-notitle | 1.000 | 0.733 | 1.000 | 0.917 | 8192 | 0 |

## Seção `## Links` no texto embedado (minilm-chunk-title)

Os wiki-links do fim da nota são nomes de outras notas, não conteúdo. Produção hoje: sem a seção.

| variante | R@5 | nDCG@5 | MRR | R@5 cauda | FP@0.55 | R@5 com t=0.55 | chunks |
|---|---|---|---|---|---|---|---|
| com `## Links` | 0.940 | 0.819 | 0.799 | 1.000 | 10% | 0.740 | 516 |
| **sem `## Links`** | 0.960 | 0.832 | 0.802 | 1.000 | 10% | 0.740 | 475 |

## Busca híbrida e rerank (minilm-chunk-title)

Rankings alternativos em cima do vetorial de produção. `bm25` é só lexical; `rrf` funde vetorial e BM25 (k=60); `weighted-a` soma a × cosseno + (1 − a) × BM25 normalizado; `rerank-X@base` reordena o top-20 da base com um cross-encoder. O corte continua no cosseno (cosseno >= 0.55), então o FP fica igual ao da produção; a coluna "t próprio" é o corte no score do reranker com FP ≤ 10%. Latência extra = BM25 + rerank por pergunta, somada à do vetorial.

| variante | R@1 | R@5 | MRR | nDCG@5 | R@5 cauda | R@5 com t=0.55 | t próprio (R@5 / FP) | +p50 ms | +p95 ms | erra no top-5 |
|---|---|---|---|---|---|---|---|---|---|---|
| **vector** | 0.720 | 0.960 | 0.802 | 0.832 | 1.000 | 0.740 | 0.55 (0.740 / 10%) | 0.0 | 0.0 | q026, q032 |
| bm25 | 0.820 | 0.860 | 0.842 | 0.809 | 1.000 | 0.740 | — | 0.1 | 0.1 | q026, q032, q034, q037, q042, q043, q050 |
| rrf | 0.820 | 0.920 | 0.856 | 0.848 | 1.000 | 0.740 | — | 0.1 | 0.1 | q026, q032, q043, q050 |
| weighted-0.5 | 0.860 | 0.900 | 0.882 | 0.850 | 1.000 | 0.740 | 0.80 (0.580 / 0%) | 0.1 | 0.1 | q026, q032, q037, q043, q050 |
| weighted-0.7 | 0.860 | 0.940 | 0.896 | 0.873 | 1.000 | 0.740 | 0.70 (0.640 / 0%) | 0.1 | 0.1 | q026, q032, q043 |
| weighted-0.9 | 0.840 | 0.940 | 0.886 | 0.876 | 1.000 | 0.740 | 0.60 (0.700 / 0%) | 0.1 | 0.1 | q026, q032, q043 |
| rerank-mminilm@vector | 0.880 | 0.940 | 0.907 | 0.881 | 0.917 | 0.740 | 0.60 (0.720 / 10%) | 4500.1 | 5880.2 | q026, q032, q040 |
| rerank-mminilm@weighted-0.9 | 0.880 | 0.940 | 0.907 | 0.881 | 0.917 | 0.740 | 0.60 (0.720 / 10%) | 4889.6 | 6155.7 | q026, q032, q040 |
| rerank-bge-reranker@vector | 0.880 | 0.980 | 0.918 | 0.912 | 1.000 | 0.740 | 0.10 (0.800 / 10%) | 57926.5 | 76736.7 | q032 |
| rerank-bge-reranker@weighted-0.9 | 0.880 | 0.980 | 0.918 | 0.912 | 1.000 | 0.740 | 0.10 (0.800 / 10%) | 59589.4 | 73680.4 | q032 |

## Expansão pelo campo related (bge-m3-chunk-notitle)

Notas relacionadas às top-3 entram com score max(próprio, λ × score da origem) e a lista é reordenada.

| variante | R@5 | nDCG@5 | MRR | R@5 cauda |
|---|---|---|---|---|
| sem expansão | 0.920 | 0.850 | 0.873 | 0.917 |
| λ = 0.8 | 0.920 | 0.846 | 0.873 | 0.917 |
| λ = 0.9 | 0.920 | 0.861 | 0.873 | 0.917 |
| λ = 1.0 | 0.900 | 0.859 | 0.869 | 0.917 |
