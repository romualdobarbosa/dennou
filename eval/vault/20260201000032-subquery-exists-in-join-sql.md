---
id: 20260201000032
title: "Subquery com IN, EXISTS ou JOIN"
type: concept
tags: [sql, subquery, exists, join]
area: programacao
created: 01/02/26
source: agent
related: [20260201000025, 20260201000030, 20260201000031]
---

## Definição
Muitas consultas do tipo "linhas de A que têm (ou não têm) correspondência em B" podem ser escritas de três formas: `IN (subquery)`, `EXISTS (subquery correlacionada)` ou `JOIN`. Elas não são sempre equivalentes, principalmente quando há `NULL` ou duplicatas.

## Como funciona
```sql
-- clientes que têm pelo menos um pedido
SELECT * FROM clientes c
WHERE c.id IN (SELECT cliente_id FROM pedidos);

SELECT * FROM clientes c
WHERE EXISTS (SELECT 1 FROM pedidos p WHERE p.cliente_id = c.id);

SELECT DISTINCT c.* FROM clientes c
JOIN pedidos p ON p.cliente_id = c.id;
```

Diferenças práticas:
- **JOIN duplica linhas**: um cliente com 10 pedidos aparece 10 vezes, por isso o `DISTINCT`. `IN` e `EXISTS` são "semi-joins": cada cliente aparece no máximo uma vez.
- **EXISTS** para assim que encontra a primeira correspondência e não se importa com o que o `SELECT` interno retorna (`SELECT 1` é convenção).
- **Para a negação, prefira NOT EXISTS**. `NOT IN` com uma subquery que retorna algum `NULL` devolve zero linhas. `NOT EXISTS` não tem esse problema, e o `LEFT JOIN ... WHERE b.id IS NULL` (anti-join) também funciona.

Desempenho: otimizadores modernos (PostgreSQL, MySQL 8, SQL Server) costumam transformar `IN` e `EXISTS` no mesmo plano de semi-join, então a escolha deve priorizar a clareza e a correção com `NULL`. Em versões antigas do MySQL, subqueries com `IN` eram notoriamente lentas, e por isso surgiu o hábito de reescrever tudo como JOIN.

Subquery escalar (que retorna um único valor) também pode aparecer no `SELECT`:

```sql
SELECT nome, (SELECT COUNT(*) FROM pedidos p WHERE p.cliente_id = c.id) AS qtd
FROM clientes c;
```

## Analogia
`EXISTS` é perguntar na portaria se "tem alguém do apartamento 12 aqui": basta achar uma pessoa. O `JOIN` é pedir a lista completa de todos os visitantes do 12, um por linha.

## Links
[[20260201000025-inner-join-sql]]
[[20260201000030-null-logica-tres-valores-sql]]
[[20260201000031-cte-with-sql]]
