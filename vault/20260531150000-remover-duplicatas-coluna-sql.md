---
id: 20260531150000
title: "Remover duplicatas por coluna no SQL"
type: syntax
tags: [sql, duplicatas, having, group-by, subquery, not-in]
area: programacao
created: 31/05/26
source: agent
related: [20260528214944, 20260528210249]
---

## O que é
Filtro para excluir da seleção todas as linhas cujo valor em uma coluna apareça mais de uma vez.

## Sintaxe
```sql
SELECT *
FROM tabela
WHERE coluna NOT IN (
    SELECT coluna
    FROM tabela
    GROUP BY coluna
    HAVING COUNT(*) > 1
);
```

## Exemplo
```sql
SELECT *
FROM usuarios
WHERE first_name NOT IN (
    SELECT first_name
    FROM usuarios
    GROUP BY first_name
    HAVING COUNT(*) > 1
);
```
Resultado: apenas linhas com `first_name` que aparece exatamente uma vez.

## Gotchas
- `HAVING COUNT(*) > 1` identifica os nomes duplicados — o `NOT IN` externo remove **todas** as ocorrências, não apenas as extras
- Se quiser manter uma das ocorrências (em vez de remover todas), use `ROW_NUMBER()` com `PARTITION BY` e filtre pelo rank
- `NOT IN` com subquery pode ter comportamento inesperado se a coluna contiver `NULL` — prefira `NOT EXISTS` nesses casos

## Links
[[20260528214944-filtrar-where-primeira-letra-sql]]
[[20260528210249-left-join-sql]]
