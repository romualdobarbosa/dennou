# Eval de geração

Gerado por `python -m eval.run_generation_eval` em 2026-11-20 (commit `7075d2c-dirty`). Busca: `minilm-chunk-title` no vault de `eval/vault`. Resposta: `claude-sonnet-5-5` via `claude -p` sem ferramentas; juiz: `claude-opus-5-5`. Uma rodada por pergunta.

| variante | nota certa no prompt | citou nota certa | citou nota irrelevante | correta (juiz) | fiel (juiz) | FP sem resposta | prompt médio (chars) |
|---|---|---|---|---|---|---|---|
| A: só notas com score >= 0.55 (hoje) | 74% | 74% | 2% | 100% | 98% | 0% (10) | 3706 |
| B: notas >= 0.55 + faixa 'talvez' de 0.45 a 0.55 | 84% | 84% | 2% | 100% | 100% | 0% (10) | 6130 |
| C: top-5 inteiro com score, o modelo decide | 96% | 96% | 6% | 100% | 98% | 0% (10) | 11686 |

Perguntas com resposta: 50. "Citou nota certa" = o modelo listou uma nota de grau 2 em used_note_ids. "FP sem resposta" = nas perguntas sem resposta no vault, citou alguma nota. "Fiel" vale para as 60 perguntas.

## Por kind (citou nota certa / correta)

| variante | literal | paraphrase | cross_lingual |
|---|---|---|---|
| A | 100% / 100% | 27% / 100% | 80% / 100% |
| B | 100% / 100% | 47% / 100% | 100% / 100% |
| C | 100% / 100% | 87% / 100% | 100% / 100% |

## Casos em que as variantes discordam

- **q009** (literal): A: citou 20260201000026, 20260201000032, correta; B: citou 20260201000026, correta; C: citou 20260201000026, 20260201000030, correta
- **q016** (literal): A: citou 20260201000038, 20260201000024, correta; B: citou 20260201000038, 20260201000024, 20260201000027, correta; C: citou 20260201000038, 20260201000024, 20260201000027, correta
- **q020** (literal): A: citou 20260201000067, correta; B: citou 20260201000067, correta; C: citou 20260201000067, 20260201000075, correta
- **q026** (paraphrase): A: citou nada, correta; B: citou nada, correta; C: citou 20260201000042, 20260201000043, 20260201000044, 20260201000057, correta
- **q029** (paraphrase): A: citou nada, correta; B: citou nada, correta; C: citou 20260201000063, correta
- **q030** (paraphrase): A: citou nada, correta; B: citou 20260201000076, correta; C: citou 20260201000076, correta
- **q033** (paraphrase): A: citou nada, correta; B: citou nada, correta; C: citou 20260201000027, correta
- **q034** (paraphrase): A: citou nada, correta; B: citou nada, correta; C: citou 20260201000029, 20260201000028, correta
- **q035** (paraphrase): A: citou nada, correta; B: citou 20260201000006, correta; C: citou 20260201000006, correta
- **q037** (paraphrase): A: citou nada, correta; B: citou 20260201000071, correta; C: citou 20260201000071, correta
- **q038** (paraphrase): A: citou nada, correta; B: citou nada, correta; C: citou 20260201000055, correta
- **q039** (paraphrase): A: citou nada, correta; B: citou nada, correta; C: citou 20260201000078, correta
- **q040** (paraphrase): A: citou nada, correta; B: citou nada, correta; C: citou 20260201000059, correta
- **q043** (cross_lingual): A: citou nada, correta; B: citou 20260201000067, correta; C: citou 20260201000067, correta
- **q046** (cross_lingual): A: citou nada, correta; B: citou 20260201000017, correta; C: citou 20260201000017, correta
