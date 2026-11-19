---
id: 20260201000007
title: "Decorators em Python"
type: concept
tags: [python, decorator, funcao]
area: programacao
created: 01/02/26
source: agent
related: [20260201000006, 20260201000015]
---

## Definição
Decorator é uma função que recebe outra função e devolve uma nova função, normalmente acrescentando comportamento antes ou depois da chamada original. A sintaxe `@decorador` é só açúcar para `func = decorador(func)`.

## Como funciona
```python
import functools
import time

def cronometrar(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        inicio = time.perf_counter()
        resultado = func(*args, **kwargs)
        print(f"{func.__name__} levou {time.perf_counter() - inicio:.3f}s")
        return resultado
    return wrapper

@cronometrar
def processar(dados):
    ...
```

O `wrapper` usa `*args, **kwargs` para aceitar qualquer assinatura e repassá-la. Sem `functools.wraps`, a função decorada perderia `__name__`, `__doc__` e outros metadados (passaria a se chamar `wrapper`), o que atrapalha debug e documentação.

Decorator com parâmetros precisa de um nível a mais: uma função que recebe os parâmetros e retorna o decorator de fato.

```python
def repetir(vezes):
    def decorador(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(vezes):
                func(*args, **kwargs)
        return wrapper
    return decorador

@repetir(3)
def ola():
    print("olá")
```

Decorators também podem ser classes (qualquer objeto chamável que receba a função) e podem ser aplicados a classes inteiras, como faz o `@dataclass`. Um uso muito comum é o cache: `@functools.lru_cache(maxsize=None)` (ou `@functools.cache`, no 3.9+) guarda o resultado de chamadas anteriores pelo valor dos argumentos.

Decorators empilhados são aplicados de baixo para cima: o mais próximo da função é aplicado primeiro. Exemplos da biblioteca padrão: `@property`, `@staticmethod`, `@classmethod`, `@functools.lru_cache`, `@dataclasses.dataclass`.

Um cuidado: o decorator roda **uma vez**, no momento em que a função é definida (normalmente na importação do módulo). Só o `wrapper` roda a cada chamada. Código pesado colocado fora do `wrapper` executa na importação, o que costuma surpreender.

## Analogia
É como embrulhar um presente: a caixa de dentro continua a mesma, mas quem recebe interage primeiro com o papel de fora.

## Links
[[20260201000006-generators-yield-python]]
[[20260201000015-args-kwargs-python]]
