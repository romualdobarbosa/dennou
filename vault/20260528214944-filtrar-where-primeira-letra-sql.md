---
id: 20260528214944
title: "Filtrar no WHERE pela primeira letra de um nome"
type: syntax
tags: [sql, where, like, filtro, string]
area: programacao
created: 28/05/26
source: agent
related: [20260528210249]
---

## O que é
Formas de filtrar registros no SQL pela primeira letra de um campo de texto.

## Sintaxe
```sql
SELECT * FROM tabela WHERE coluna LIKE 'A%';
```

## Exemplo
```sql
-- Começa com A
SELECT * FROM clientes WHERE nome LIKE 'A%';

-- Case-insensitive (PostgreSQL)
SELECT * FROM clientes WHERE nome ILIKE 'a%';

-- Começa com A, B ou C via IN
SELECT * FROM clientes WHERE LEFT(nome, 1) IN ('A', 'B', 'C');

-- Usando função LEFT() diretamente
SELECT * FROM clientes WHERE LEFT(nome, 1) = 'A';
```

## Gotchas
- `LIKE` é case-sensitive no PostgreSQL; use `ILIKE` para ignorar maiúsculas/minúsculas
- `ILIKE` é exclusivo do PostgreSQL — em MySQL use `LIKE` (já é case-insensitive por padrão para collations `_ci`)
- `LEFT(nome, 1)` é útil quando comparar com múltiplos valores via `IN`
- `LIKE 'A%'` é mais portável entre bancos do que funções como `LEFT()`

## Links
[[20260528210249-left-join-sql]]
