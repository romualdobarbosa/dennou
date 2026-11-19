---
id: 20260201000016
title: "Diferença entre is e == em Python"
type: concept
tags: [python, comparacao, identidade]
area: programacao
created: 01/02/26
source: agent
related: [20260201000017]
---

## Definição
`==` compara **valor** (chama `__eq__`); `is` compara **identidade**, ou seja, se os dois nomes apontam para o mesmo objeto na memória (mesmo `id()`).

## Como funciona
```python
a = [1, 2]
b = [1, 2]
a == b   # True: mesmo conteúdo
a is b   # False: objetos diferentes
c = a
c is a   # True
```

Use `is` só para singletons: `x is None`, `x is True`. O CPython guarda em cache inteiros pequenos (de -5 a 256), então `x is 256` pode dar `True` por acaso e `x is 1000` dar `False`. Comparar números ou strings com `is` é bug; versões recentes emitem `SyntaxWarning` quando há literal envolvido.

## Analogia
`==` pergunta se duas pessoas têm o mesmo nome; `is` pergunta se é a mesma pessoa.

## Links
[[20260201000017-gerenciamento-memoria-python]]
