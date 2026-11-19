---
id: 20260201000046
title: "Merge fast-forward vs merge commit no Git"
type: concept
tags: [git, merge, branch]
area: programacao
created: 01/02/26
source: agent
related: [20260201000045, 20260201000047]
---

## Definição
Um merge é **fast-forward** quando o branch de destino não tem commits novos desde que o outro branch saiu dele. Nesse caso, o Git só avança o ponteiro, sem criar commit de merge. Se os dois lados divergiram, o Git cria um **merge commit** com dois pais.

## Como funciona
```bash
git switch main
git merge feature            # fast-forward se possível
git merge --no-ff feature    # sempre cria merge commit
git merge --ff-only feature  # falha se não der fast-forward
```

`--no-ff` preserva no histórico o agrupamento dos commits da feature. `--ff-only` garante que nada novo seja criado sem você perceber.

## Analogia
Se ninguém andou na estrada principal desde que você pegou o desvio, basta mover a placa "você está aqui" para o fim do desvio. Se andaram, é preciso construir um entroncamento.

## Links
[[20260201000045-git-rebase]]
[[20260201000047-conflito-de-merge-git]]
