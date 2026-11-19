---
id: 20260201000018
title: "Type hints em Python"
type: syntax
tags: [python, tipagem, type-hints]
area: programacao
created: 01/02/26
source: agent
related: [20260201000015]
---

## O que é
Anotações de tipo opcionais para parâmetros, retornos e variáveis. O interpretador **não** as verifica em tempo de execução: elas servem a ferramentas como mypy, pyright e às IDEs, além de documentar o código.

## Sintaxe
```python
def saudacao(nome: str, vezes: int = 1) -> str:
    return f"Olá, {nome}! " * vezes

idade: int = 30
nomes: list[str] = []                 # genéricos nativos (3.9+)
mapa: dict[str, int] = {}
talvez: int | None = None             # união com | (3.10+)
```

## Exemplo
```python
from typing import Optional, Callable, Iterable

def primeiro(itens: Iterable[str]) -> Optional[str]:
    for item in itens:
        return item
    return None

def aplicar(f: Callable[[int], int], x: int) -> int:
    return f(x)
```

Antes do 3.9 era preciso importar `List`, `Dict` etc. de `typing`; hoje `list[str]` e `dict[str, int]` funcionam direto. `Optional[X]` é o mesmo que `X | None`. Para aliases, o Python 3.12 introduziu a instrução `type`:

```python
type Ponto = tuple[float, float]
```

Para dicionários com chaves fixas existe `TypedDict`; para interfaces estruturais ("qualquer coisa que tenha o método X"), `Protocol`.

## Gotchas
- Errar o tipo não gera erro ao executar: `saudacao(42)` roda normalmente. Quem acusa é o verificador estático.
- `Optional[int]` não significa "parâmetro opcional"; significa "pode ser `None`". Um parâmetro só é opcional se tiver valor padrão.
- Em tempo de execução as anotações ficam acessíveis em `funcao.__annotations__` (ou via `typing.get_type_hints`), e bibliotecas como Pydantic e dataclasses as usam para validar ou gerar código.
- Referência a uma classe ainda não definida exige aspas (`"Arvore"`) ou `from __future__ import annotations`.

## Links
[[20260201000015-args-kwargs-python]]
