---
id: 20260201000003
title: "Dicionários em Python e o método get"
type: syntax
tags: [python, dicionario, estrutura-de-dados]
area: programacao
created: 01/02/26
source: agent
related: [20260201000002, 20260201000010]
---

## O que é
Mapeamento chave → valor. Mutável, e desde o Python 3.7 preserva a ordem de inserção.

## Sintaxe
```python
d = {"a": 1}
d["b"] = 2               # insere/atualiza
d.get("c")               # None se a chave não existir
d.get("c", 0)            # valor padrão
d.setdefault("c", [])    # insere o padrão se faltar e retorna
for k, v in d.items():
    ...
```

## Exemplo
```python
contagem = {}
for palavra in ["a", "b", "a"]:
    contagem[palavra] = contagem.get(palavra, 0) + 1
# {'a': 2, 'b': 1}
```

## Gotchas
- Chaves precisam ser hashable (str, int, tupla de imutáveis).
- Para contagens, `collections.Counter` resolve em uma linha.

## Links
[[20260201000002-tuplas-python]]
[[20260201000010-keyerror-python]]
