---
id: 20260201000038
title: "Erro: column must appear in the GROUP BY clause"
type: error
tags: [sql, group-by, postgresql, agregacao]
area: programacao
created: 01/02/26
source: agent
related: [20260201000024, 20260201000023]
---

## Erro
```
ERROR: column "pedidos.data" must appear in the GROUP BY clause
or be used in an aggregate function
```

## Causa
O `SELECT` tem uma coluna que não está no `GROUP BY` nem dentro de uma agregação. Como cada grupo vira uma linha, o banco não sabe qual dos vários valores daquela coluna mostrar.

## Solução
```sql
-- agregue a coluna
SELECT cliente_id, MAX(data) FROM pedidos GROUP BY cliente_id;
-- ou inclua-a no agrupamento
SELECT cliente_id, data, COUNT(*) FROM pedidos GROUP BY cliente_id, data;
```

## Contexto
Mensagem do PostgreSQL. O MySQL com `ONLY_FULL_GROUP_BY` (padrão desde o 5.7) dá erro parecido. Se o objetivo é "a linha inteira do pedido mais recente por cliente", use window function com `ROW_NUMBER()`.

## Links
[[20260201000024-group-by-agregacao-sql]]
[[20260201000023-having-sql]]
