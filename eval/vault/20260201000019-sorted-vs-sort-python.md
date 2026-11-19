---
id: 20260201000019
title: "sorted() vs list.sort() em Python"
type: syntax
tags: [python, lista, ordenacao]
area: programacao
created: 01/02/26
source: agent
related: [20260201000001]
---

## O que é
Duas formas de ordenar em Python. `list.sort()` ordena a própria lista **no lugar** e retorna `None`. `sorted(iteravel)` aceita qualquer iterável e retorna uma **nova lista** ordenada, sem alterar o original.

## Sintaxe
```python
nums.sort()                         # altera nums, retorna None
novos = sorted(nums)                # nums continua igual
sorted(itens, key=len)              # critério de ordenação
sorted(itens, reverse=True)         # decrescente
```

## Exemplo
```python
pessoas = [("Ana", 31), ("Bia", 25), ("Caio", 31)]

# por idade, e em empate por nome
sorted(pessoas, key=lambda p: (p[1], p[0]))

from operator import itemgetter
sorted(pessoas, key=itemgetter(1), reverse=True)

# ordenar um dict pelos valores
precos = {"pão": 8, "café": 25, "leite": 6}
sorted(precos.items(), key=lambda kv: kv[1])
```

A ordenação do Python (Timsort, e a partir do 3.11 uma variante com política de merge "powersort") é **estável**: elementos com chave igual mantêm a ordem relativa original. Isso permite ordenar em vários passes, do critério menos importante para o mais importante.

```python
dados.sort(key=lambda d: d["nome"])
dados.sort(key=lambda d: d["idade"])   # por idade; empates continuam por nome
```

## Gotchas
- `nums = nums.sort()` é um erro clássico: `nums` vira `None`.
- `key` recebe uma função que é chamada uma vez por elemento; é mais eficiente do que comparar pares.
- Ordenar strings com acento usa a ordem dos códigos Unicode, então "Ábaco" vem depois de "Zebra". Para ordem alfabética "humana", use `locale.strxfrm` como key.
- Para pegar só os N maiores ou menores sem ordenar tudo, `heapq.nlargest(n, itens, key=...)` e `heapq.nsmallest` são mais eficientes quando N é pequeno.
- Misturar tipos incomparáveis, como `int` e `str`, levanta `TypeError` no Python 3.

## Links
[[20260201000001-listas-python]]
