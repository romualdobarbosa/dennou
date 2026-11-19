---
id: 20260201000055
title: "Erro: push rejeitado (non-fast-forward / fetch first)"
type: error
tags: [git, push, remoto]
area: programacao
created: 01/02/26
source: agent
related: [20260201000058, 20260201000045]
---

## Erro
```
! [rejected]        main -> main (fetch first)
error: failed to push some refs to 'origin'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

## Causa
O branch remoto tem commits que o seu branch local não tem. Aceitar o push apagaria esses commits, então o servidor recusa.

## Solução
```bash
git pull --rebase origin main   # integra o trabalho remoto e reaplica o seu por cima
git push
```

## Contexto
Comum quando outra pessoa (ou você em outra máquina) enviou commits antes. Depois de um rebase ou `--amend` em commits já publicados, o push exige força; nesse caso use `git push --force-with-lease`, que recusa se o remoto mudou desde o seu último fetch, em vez de `--force`, que sobrescreve qualquer coisa.

## Links
[[20260201000058-git-fetch-vs-pull]]
[[20260201000045-git-rebase]]
