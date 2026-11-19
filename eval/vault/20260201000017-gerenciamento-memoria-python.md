---
id: 20260201000017
title: "Gerenciamento de memória no CPython: contagem de referências e coletor de ciclos"
type: concept
tags: [python, memoria, garbage-collector]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000013, 20260201000016]
---

## Definição
O CPython libera memória principalmente por **contagem de referências**: cada objeto guarda quantas referências apontam para ele, e quando esse número chega a zero o objeto é destruído na hora. Para os casos em que isso não basta, existe um **coletor de lixo de ciclos**, implementado no módulo `gc`.

## Como funciona
### Contagem de referências
Uma referência é criada quando um objeto é atribuído a um nome, colocado numa lista, passado como argumento etc. Ela some quando o nome sai de escopo, é reatribuído, ou quando usamos `del`.

```python
a = []        # contagem = 1
b = a         # contagem = 2
del a         # contagem = 1 (del remove o NOME, não o objeto)
b = None      # contagem = 0 -> lista liberada imediatamente
```

A grande vantagem é a previsibilidade: a memória volta assim que o último dono solta o objeto. É por isso que, no CPython, um arquivo aberto sem `with` costuma ser fechado logo que a variável deixa de existir, embora depender disso seja má prática.

### Ciclos de referência
A contagem falha quando objetos apontam uns para os outros:

```python
a = {}
b = {"a": a}
a["b"] = b
del a, b      # os dois dicts continuam com contagem 1
```

Nenhum código consegue mais alcançar esses objetos, mas o contador nunca chega a zero. O coletor de ciclos percorre periodicamente os objetos contêineres (listas, dicts, instâncias de classes), detecta grupos inalcançáveis e os libera. Historicamente ele é **geracional**: objetos novos ficam numa geração jovem, verificada com frequência; os que sobrevivem são promovidos para gerações mais velhas, verificadas menos vezes. Os limiares que disparam a coleta podem ser consultados com `gc.get_threshold()`, e versões recentes do Python vêm mudando esses detalhes internos, então consulte a documentação da sua versão.

```python
import gc
gc.collect()          # força uma coleta completa e retorna quantos objetos achou
gc.disable()          # desliga só o coletor de ciclos; a contagem continua
```

Desde o Python 3.4 (PEP 442), objetos com `__del__` que participam de ciclos também podem ser coletados.

### Referências fracas
O módulo `weakref` permite apontar para um objeto **sem** aumentar a contagem. É útil em caches e em estruturas pai/filho, para que o filho não mantenha o pai vivo:

```python
import weakref
cache = weakref.WeakValueDictionary()
```

### Alocador e devolução de memória ao sistema
Objetos pequenos (até 512 bytes, desde o Python 3.8) são alocados pelo `pymalloc`, que reserva blocos grandes do sistema operacional e os divide internamente. Por isso, liberar objetos nem sempre faz o processo encolher no gerenciador de tarefas: a memória pode ficar reservada para reuso dentro do próprio processo. Para investigar consumo, use `tracemalloc`:

```python
import tracemalloc
tracemalloc.start()
# ... código ...
for stat in tracemalloc.take_snapshot().statistics("lineno")[:5]:
    print(stat)
```

### Inspecionando a contagem: sys.getrefcount
`sys.getrefcount(obj)` mostra a contagem atual, mas o valor retornado é **sempre um a mais** do que você espera. O motivo é que passar o objeto como argumento para a própria função cria uma referência temporária, que existe durante a chamada:

```python
import sys
x = []
sys.getrefcount(x)    # 2: o nome x + o argumento temporário
```

Outro detalhe: desde o Python 3.12 (PEP 683), alguns objetos são **imortais**, como `None`, `True`, `False` e inteiros pequenos. A contagem deles não muda de verdade, e `sys.getrefcount(None)` devolve um número enorme e fixo, que não reflete quantas referências existem. A ideia é evitar escrita na memória desses objetos compartilhados, o que ajuda no desempenho e no free-threading.

## Analogia
A contagem de referências é como um livro de biblioteca que só volta para a estante quando o último leitor o devolve. O coletor de ciclos é o funcionário que de vez em quando passa pelas mesas e recolhe livros que só estão "emprestados" uns para os outros, sem nenhum leitor de verdade.

## Links
[[20260201000013-gil-python]]
[[20260201000016-is-vs-igual-python]]
