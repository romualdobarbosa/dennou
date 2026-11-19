---
id: 20260201000009
title: "Argumento padrão mutável compartilhado entre chamadas"
type: error
tags: [python, funcao, bug]
area: programacao
created: 01/02/26
source: agent
related: [20260201000001, 20260201000015]
---

## Erro
Função com `def f(item, lista=[])` acumula valores de chamadas anteriores: a segunda chamada já começa com os itens da primeira.

## Causa
Valores padrão são avaliados **uma única vez**, quando o `def` é executado, e não a cada chamada. A mesma lista é reaproveitada em todas as chamadas que não passam o argumento.

## Solução
```python
def adicionar(item, lista=None):
    if lista is None:
        lista = []
    lista.append(item)
    return lista
```

## Contexto
Vale para qualquer padrão mutável: `[]`, `{}`, `set()`, objetos. Linters como o Ruff (regra B006) e o pylint avisam sobre isso.

## Links
[[20260201000001-listas-python]]
[[20260201000015-args-kwargs-python]]
