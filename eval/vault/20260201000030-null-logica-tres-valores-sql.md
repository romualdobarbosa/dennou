---
id: 20260201000030
title: "NULL e a lógica de três valores no SQL"
type: concept
tags: [sql, null, logica]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000022, 20260201000026]
---

## Definição
`NULL` representa valor **desconhecido** ou ausente. Qualquer comparação com `NULL` resulta em `UNKNOWN`, um terceiro valor lógico além de `TRUE` e `FALSE`. O `WHERE` só mantém linhas cuja condição é `TRUE`.

## Como funciona
```sql
NULL = NULL      -- UNKNOWN, não TRUE
WHERE x IS NULL          -- forma correta
WHERE x IS DISTINCT FROM y   -- compara tratando NULL como valor
COALESCE(desconto, 0)        -- troca NULL por um padrão
```

Armadilha clássica: `WHERE id NOT IN (SELECT cliente_id FROM ...)` retorna **zero linhas** se a subconsulta tiver algum `NULL`, porque `x <> NULL` é `UNKNOWN`. Use `NOT EXISTS`.

## Analogia
Perguntar se a idade de um desconhecido é igual à de outro desconhecido: a resposta honesta não é "sim" nem "não", é "não sei".

## Links
[[20260201000022-where-sql]]
[[20260201000026-left-join-sql]]
