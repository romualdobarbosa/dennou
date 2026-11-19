---
id: 20260201000015
title: "*args e **kwargs em Python"
type: syntax
tags: [python, funcao, argumentos]
area: programacao
created: 01/02/26
source: agent
related: [20260201000007, 20260201000009]
---

## O que é
`*args` captura argumentos posicionais extras numa **tupla**; `**kwargs` captura argumentos nomeados extras num **dicionário**. Os nomes são convenção; o que importa são os asteriscos.

## Sintaxe
```python
def f(a, *args, chave=None, **kwargs):
    ...

f(1, 2, 3, chave="x", extra=True)
# a=1, args=(2, 3), chave="x", kwargs={'extra': True}
```

## Exemplo
```python
def somar(*numeros):
    return sum(numeros)

valores = [1, 2, 3]
somar(*valores)          # desempacota a lista
config = {"sep": "-"}
print("a", "b", **config)  # a-b
```

## Gotchas
- Ordem obrigatória: posicionais, `*args`, nomeados, `**kwargs`.
- Parâmetros depois de `*args` só podem ser passados por nome.

## Links
[[20260201000007-decorators-python]]
[[20260201000009-argumento-padrao-mutavel-python]]
