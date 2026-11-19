---
id: 20260201000040
title: "Ordem lógica de execução de um SELECT"
type: fact
tags: [sql, select, where, having]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000022, 20260201000023, 20260201000024]
---

## Resposta
A ordem em que o SQL **avalia** as cláusulas é diferente da ordem em que são escritas:

1. `FROM` / `JOIN`
2. `WHERE`
3. `GROUP BY`
4. `HAVING`
5. `SELECT` (inclusive window functions)
6. `DISTINCT`
7. `ORDER BY`
8. `LIMIT` / `OFFSET`

## Contexto
Isso explica vários erros: um alias criado no `SELECT` não existe no `WHERE`, mas pode ser usado no `ORDER BY`; agregações não cabem no `WHERE` porque os grupos ainda não existem; window functions não podem ser filtradas no `WHERE`. O otimizador pode executar fisicamente em outra ordem, desde que o resultado seja equivalente.

## Fonte
Ordem lógica de processamento descrita na documentação do SQL Server e em textos sobre o padrão SQL.

## Links
[[20260201000022-where-sql]]
[[20260201000023-having-sql]]
[[20260201000024-group-by-agregacao-sql]]
