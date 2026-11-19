---
id: 20260201000054
title: "Erro: refusing to merge unrelated histories"
type: error
tags: [git, merge, pull, remoto]
area: programacao
created: 01/02/26
source: agent
related: [20260201000046, 20260201000058]
---

## Erro
```
fatal: refusing to merge unrelated histories
```

## Causa
Os dois branches não têm nenhum commit em comum. Caso típico: você criou o repositório no GitHub com README ou licença, criou outro repositório local com `git init` e tentou fazer `git pull` de um no outro. O Git recusa por padrão desde a versão 2.9.

## Solução
```bash
git pull origin main --allow-unrelated-histories
# resolva conflitos (ex.: README nos dois lados), depois:
git push -u origin main
```

## Contexto
Também aparece ao juntar dois projetos independentes num só repositório. Se o histórico remoto não importa (repositório recém-criado), uma alternativa é `git push --force` do local, sabendo que isso apaga o que está no remoto.

## Links
[[20260201000046-git-merge-fast-forward]]
[[20260201000058-git-fetch-vs-pull]]
