# Eval de geração, modo agente

Gerado por `python -m eval.run_agent_eval` em 2026-11-20 (commit `7075d2c-dirty`). Cada pergunta roda o `claude -p` do bot (`sonnet`, mesmas ferramentas e permissões) numa cópia do projeto com o vault de `eval/vault`. Juiz: `opus`. Uma rodada por pergunta; perguntas dos tipos paraphrase, cross_lingual, no_answer.

| regra | buscou no vault | nota certa apareceu na busca | citou nota certa | só abaixo do corte: citou | citou nota irrelevante | fiel | FP sem resposta | notas abertas (média) | abriu nota abaixo do corte | tempo médio |
|---|---|---|---|---|---|---|---|---|---|---|
| corte: ignora notas abaixo de 0.55 | 97% | 92% | 76% | 0% (4) | 8% | 94% | 0% (10) | 0.1 | 0% | 14 s |
| pista: score como pista, abre a nota | 100% | 92% | 96% | 100% (5) | 4% | 94% | 0% (10) | 0.8 | 17% | 14 s |

"Só abaixo do corte" = perguntas em que a nota certa veio na busca, mas só com score < 0.55 (são as que a regra atual manda ignorar).

## Por kind (citou nota certa)

| regra | paraphrase | cross_lingual |
|---|---|---|
| corte | 73% | 80% |
| pista | 100% | 90% |

## Casos em que as regras discordam

- **q026** (paraphrase): corte: abriu nada, citou 20260201000044; pista: abriu 20260201000042, 20260201000049, citou 20260201000042, 20260201000044, 20260201000049
- **q030** (paraphrase): corte: abriu nada, citou nada; pista: abriu 20260201000076, citou 20260201000076
- **q036** (paraphrase): corte: abriu nada, citou nada; pista: abriu 20260201000033, citou 20260201000033
- **q040** (paraphrase): corte: abriu nada, citou nada; pista: abriu 20260201000059, citou 20260201000059
- **q041** (cross_lingual): corte: abriu nada, citou 20260201000043; pista: abriu 20260201000042, citou 20260201000042, 20260201000043
- **q043** (cross_lingual): corte: abriu nada, citou 20260201000067, 20260201000075; pista: abriu 20260201000067, citou 20260201000067 (infiel)
- **q048** (cross_lingual): corte: abriu nada, citou 20260201000020 (infiel); pista: abriu 20260201000020, citou 20260201000020
