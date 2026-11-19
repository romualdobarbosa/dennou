---
id: 20260201000006
title: "Generators e yield em Python"
type: concept
tags: [python, generator, iterador, lazy]
area: programacao
created: 01/02/26
source: agent
related: [20260201000005, 20260201000007]
---

## Definição
Generator é uma função que usa `yield` em vez de (ou além de) `return`. Ao ser chamada, ela não executa o corpo: devolve um objeto generator, que é um iterador. Cada `next()` roda o corpo até o próximo `yield`, entrega o valor e **pausa**, guardando variáveis locais e a posição de execução.

## Como funciona
```python
def contar_ate(n):
    i = 1
    while i <= n:
        yield i
        i += 1

g = contar_ate(3)
next(g)   # 1
next(g)   # 2
list(g)   # [3]  (consome o resto)
```

Quando a função termina, o generator levanta `StopIteration`, que o `for` trata sozinho. Os valores são produzidos sob demanda (avaliação preguiçosa), então dá pra processar arquivos enormes ou sequências infinitas sem carregar tudo na memória:

```python
def linhas_com_erro(caminho):
    with open(caminho) as f:
        for linha in f:
            if "ERROR" in linha:
                yield linha
```

Pontos importantes:
- Um generator só pode ser percorrido **uma vez**. Depois de esgotado, iterar de novo não produz nada.
- `yield from outro_iteravel` delega a produção de valores para outro iterável.
- Generator expressions `(x * 2 for x in dados)` são a versão em uma linha; `sum(x * 2 for x in dados)` nem precisa dos parênteses extras.
- `len()` não funciona em generator, porque o tamanho não é conhecido sem consumir.

## Analogia
É como uma torneira em vez de um balde: você não enche um balde com toda a água antes de usar; abre a torneira e pega um copo de cada vez, quando precisa.

## Links
[[20260201000005-list-comprehension-python]]
[[20260201000007-decorators-python]]
