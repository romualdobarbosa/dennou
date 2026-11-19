---
id: 20260201000020
title: "Tratamento de exceções em Python: try, except, else, finally"
type: syntax
tags: [python, excecao, erro]
area: programacao
created: 01/02/26
source: agent
related: [20260201000008, 20260201000010]
---

## O que é
O bloco `try` delimita código que pode falhar; `except` trata exceções específicas; `else` roda só se nada falhou; `finally` roda sempre, com ou sem erro. É a forma padrão de lidar com erros em Python, que segue o estilo EAFP ("é mais fácil pedir perdão do que permissão").

## Sintaxe
```python
try:
    valor = int(texto)
except ValueError as e:
    print(f"inválido: {e}")
except (TypeError, KeyError):
    print("tipo ou chave errada")
else:
    print("convertido sem erro")
finally:
    print("sempre executa")
```

## Exemplo
```python
def ler_config(caminho):
    try:
        f = open(caminho, encoding="utf-8")
    except FileNotFoundError:
        return {}
    else:
        with f:
            return json.load(f)
```

### EAFP vs LBYL
Há dois estilos de lidar com situações que podem falhar. LBYL ("olhe antes de pular") testa antes de agir: `if chave in d: valor = d[chave]`. EAFP ("mais fácil pedir perdão") tenta direto e trata a exceção: `try: valor = d[chave] except KeyError: ...`. Em Python, EAFP é o estilo idiomático. Ele evita condições de corrida, como verificar que um arquivo existe e ele ser apagado antes do `open`, e evita fazer a mesma busca duas vezes. LBYL continua fazendo sentido quando a falha é o caso comum, porque levantar e capturar exceções custa mais do que um `if`.

### O papel do else
O `else` existe para deixar o `try` o menor possível: só a linha que pode levantar a exceção esperada fica dentro dele. Assim você não captura por engano um erro que veio de outra linha.

### Ordem dos except
Os `except` são testados de cima para baixo e o primeiro compatível vence. Como as exceções formam uma hierarquia de classes, coloque as mais específicas primeiro: um `except Exception` no topo engoliria um `except ValueError` logo abaixo.

### Relançar e encadear
```python
try:
    processar()
except ValueError:
    log.exception("falhou")
    raise                       # relança a mesma exceção, com o traceback original

try:
    conectar()
except OSError as e:
    raise ErroDeConexao("banco indisponível") from e   # encadeamento explícito
```

Com `from e`, a exceção original fica em `__cause__` e o traceback mostra "The above exception was the direct cause of the following exception". Se você levanta uma nova exceção dentro de um `except` sem `from`, o Python guarda a original em `__context__` e mostra "During handling of the above exception, another exception occurred". Para esconder o contexto, use `raise NovaExcecao(...) from None`.

### Exceções próprias
```python
class SaldoInsuficiente(Exception):
    def __init__(self, saldo, valor):
        super().__init__(f"saldo {saldo} menor que {valor}")
        self.saldo = saldo
        self.valor = valor
```

Herde de `Exception`, nunca diretamente de `BaseException`.

### O perigo do except genérico
Um `except:` sem tipo captura **tudo**, inclusive `KeyboardInterrupt` (Ctrl+C) e `SystemExit`, que herdam de `BaseException`. Isso pode deixar o programa impossível de interromper. Se precisar de um tratamento amplo, use `except Exception` e registre o erro com `log.exception`.

### return dentro de finally
Um `return` dentro de `finally` sobrescreve o retorno do `try` e **descarta silenciosamente** qualquer exceção em andamento. A PEP 765 fez o Python 3.14 emitir `SyntaxWarning` para `return`, `break` e `continue` que saem de um `finally`.

## Gotchas
### Várias exceções ao mesmo tempo: ExceptionGroup e except*
Às vezes várias operações independentes falham juntas, por exemplo tarefas concorrentes num `asyncio.TaskGroup`. O Python 3.11 (PEP 654) introduziu `ExceptionGroup`, que carrega uma lista de exceções, e a sintaxe `except*`, que trata cada tipo dentro do grupo separadamente:

```python
try:
    raise ExceptionGroup("várias falhas", [ValueError("a"), TypeError("b")])
except* ValueError as grupo:
    print("valores:", grupo.exceptions)
except* TypeError as grupo:
    print("tipos:", grupo.exceptions)
```

Diferente do `except` comum, mais de um bloco `except*` pode executar para o mesmo grupo. Não dá para misturar `except` e `except*` no mesmo `try`.

### Anotar uma exceção com add_note
Também no 3.11 (PEP 678), toda exceção ganhou o método `add_note()`, que anexa texto extra exibido no traceback, útil para acrescentar contexto sem trocar o tipo da exceção:

```python
try:
    carregar(linha)
except ValueError as e:
    e.add_note(f"linha {numero} do arquivo")
    raise
```

## Links
[[20260201000008-context-managers-with-python]]
[[20260201000010-keyerror-python]]
