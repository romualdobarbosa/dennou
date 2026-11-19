---
id: 20260201000053
title: "Detached HEAD no Git"
type: error
tags: [git, head, branch]
area: programacao
created: 01/02/26
source: agent
related: [20260201000049, 20260201000051]
---

## Erro
```
You are in 'detached HEAD' state. You can look around, make experimental
changes and commit them...
```

## Causa
O HEAD aponta direto para um commit, e não para um branch. Acontece ao fazer `git checkout <sha>`, `git checkout v1.0` (tag), `git checkout origin/main` e durante rebase ou bisect.

## Solução
```bash
git switch main                 # só olhando: volte para um branch
git switch -c nova-branch       # fez commits que quer manter: crie um branch aqui
```

## Contexto
Commits feitos em detached HEAD não pertencem a nenhum branch. Ao sair dali sem criar um branch, eles ficam "soltos" e só são recuperáveis pelo `git reflog` até expirarem.

## Links
[[20260201000049-git-reflog]]
[[20260201000051-git-bisect]]
