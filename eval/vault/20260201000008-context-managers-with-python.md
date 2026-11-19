---
id: 20260201000008
title: "Context managers e o bloco with"
type: syntax
tags: [python, context-manager, arquivo]
area: programacao
created: 01/02/26
source: agent
related: [20260201000020, 20260201000007]
---

## O que é
O `with` garante que um recurso seja liberado ao final do bloco, mesmo se ocorrer exceção. Funciona com qualquer objeto que implemente `__enter__` e `__exit__`.

## Sintaxe
```python
with open("dados.txt", encoding="utf-8") as f:
    conteudo = f.read()
# aqui o arquivo já está fechado
```

## Exemplo
```python
from contextlib import contextmanager

@contextmanager
def mudar_dir(caminho):
    import os
    anterior = os.getcwd()
    os.chdir(caminho)
    try:
        yield
    finally:
        os.chdir(anterior)
```

## Gotchas
- Vários recursos no mesmo `with`: `with open(a) as x, open(b) as y:`.
- Sem o `try/finally` dentro do `@contextmanager`, a limpeza não roda se o bloco levantar exceção.

## Links
[[20260201000020-excecoes-try-except-python]]
[[20260201000007-decorators-python]]
