---
id: 20260101000002
title: "Dicionários em Python"
type: syntax
tags: [python, dicionario, estrutura-de-dados]
area: programacao
created: 01/01/26
source: agent
related: [20260101000001]
---

## O que é
Estrutura de chave-valor, mutável e não-ordenada (ordem de inserção preservada no Python 3.7+).

## Sintaxe
```python
d = {"chave": "valor"}
d["nova"] = 123        # inserir/atualizar
d.get("chave")         # acesso seguro (retorna None se não existir)
d.keys()               # todas as chaves
d.values()             # todos os valores
d.items()              # pares (chave, valor)
del d["chave"]         # remover
```

## Exemplo
```python
usuario = {"nome": "Ana", "idade": 30}
usuario["email"] = "ana@exemplo.com"

for chave, valor in usuario.items():
    print(f"{chave}: {valor}")
```

## Gotchas
- Acessar chave inexistente com `d["x"]` levanta `KeyError` — prefira `d.get("x")`
- Chaves devem ser imutáveis (string, int, tuple) — não pode usar lista como chave

## Links
[[20260101000001-listas-python]]
