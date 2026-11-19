---
id: 20260201000047
title: "Conflito de merge no Git"
type: error
tags: [git, merge, conflito]
area: programacao
created: 01/02/26
source: agent
related: [20260201000046, 20260201000045]
---

## Erro
```
Auto-merging app.py
CONFLICT (content): Merge conflict in app.py
Automatic merge failed; fix conflicts and then commit the result.
```

## Causa
Os dois branches alteraram as mesmas linhas de um arquivo (ou um alterou e o outro apagou o arquivo), e o Git não consegue decidir sozinho qual versão vale.

## Solução
O Git marca o trecho em conflito dentro do arquivo:

```text
<<<<<<< HEAD
timeout = 30
=======
timeout = 60
>>>>>>> feature/timeout
```

A parte de cima é a versão do branch atual (HEAD); a de baixo, a do branch que está chegando. Edite o arquivo deixando o conteúdo final correto, remova os marcadores e finalize:

```bash
git status                         # lista arquivos em conflito ("both modified")
# edita os arquivos
git add app.py
git commit                         # conclui o merge
```

Atalhos para ficar inteiro com um lado:

```bash
git checkout --ours app.py         # mantém a versão do branch atual
git checkout --theirs app.py       # mantém a versão do branch que chega
git merge --abort                  # desiste do merge e volta ao estado anterior
```

Para ver também o ancestral comum no meio dos marcadores, o que ajuda a entender o que cada lado mudou, configure:

```bash
git config --global merge.conflictStyle zdiff3   # Git 2.35+; em versões antigas use diff3
```

## Contexto
Comum em arquivos editados por muita gente ao mesmo tempo, como arquivos de configuração, listas de dependências e lockfiles. Branches curtos e integração frequente reduzem a quantidade e o tamanho dos conflitos. Ferramentas visuais podem ser abertas com `git mergetool`. Conflitos também aparecem em `git rebase`, `git cherry-pick` e `git stash pop`, e a resolução é a mesma: editar, `git add` e continuar a operação.

## Links
[[20260201000046-git-merge-fast-forward]]
[[20260201000045-git-rebase]]
