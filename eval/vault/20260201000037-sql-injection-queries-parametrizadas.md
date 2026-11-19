---
id: 20260201000037
title: "SQL injection e queries parametrizadas"
type: concept
tags: [sql, seguranca, python, sql-injection]
area: programacao
created: 01/02/26
source: agent
related: [20260201000022]
---

## Definição
SQL injection acontece quando texto vindo do usuário é concatenado na string da consulta e passa a ser interpretado como SQL. Com a entrada `' OR '1'='1`, um filtro de login vira sempre verdadeiro.

## Como funciona
```python
# VULNERÁVEL
cur.execute(f"SELECT * FROM usuarios WHERE email = '{email}'")

# SEGURO: parâmetros enviados separados da consulta
cur.execute("SELECT * FROM usuarios WHERE email = ?", (email,))     # sqlite3
cur.execute("SELECT * FROM usuarios WHERE email = %s", (email,))    # psycopg
```

Com parâmetros, o driver nunca mistura o valor com o código SQL. Nomes de tabela ou coluna não podem ser parametrizados: valide-os contra uma lista fixa permitida.

## Analogia
É como preencher um formulário em que alguém escreve no campo "nome" uma instrução para o atendente. Parametrizar é o atendente ler o campo sempre como nome, nunca como ordem.

## Links
[[20260201000022-where-sql]]
