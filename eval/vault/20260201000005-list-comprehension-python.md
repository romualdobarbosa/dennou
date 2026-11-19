---
id: 20260201000005
title: "List comprehension em Python"
type: syntax
tags: [python, lista, comprehension]
area: programacao
created: 01/02/26
source: agent
related: [20260201000001, 20260201000006]
---

## O que é
Forma compacta de construir uma lista a partir de um iterável, com transformação e filtro opcionais.

## Sintaxe
```python
[expressao for item in iteravel if condicao]
{k: v for k, v in pares}        # dict comprehension
{x for x in itens}              # set comprehension
(x for x in itens)              # generator expression
```

## Exemplo
```python
quadrados_pares = [n * n for n in range(10) if n % 2 == 0]
# [0, 4, 16, 36, 64]
rotulos = ["par" if n % 2 == 0 else "ímpar" for n in range(3)]
```

## Gotchas
- O `if` no final filtra; o `if/else` antes do `for` escolhe o valor.
- Comprehension aninhada demais fica ilegível: prefira um `for` normal.

## Links
[[20260201000001-listas-python]]
[[20260201000006-generators-yield-python]]
