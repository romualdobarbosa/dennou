---
id: 20260201000035
title: "UNION vs UNION ALL"
type: syntax
tags: [sql, union, conjunto]
area: programacao
created: 01/02/26
source: agent
related: [20260201000031]
---

## O que é
Empilham o resultado de duas ou mais consultas. `UNION` remove linhas duplicadas; `UNION ALL` mantém todas.

## Sintaxe
```sql
SELECT email FROM clientes
UNION            -- sem duplicatas
SELECT email FROM fornecedores;

SELECT email FROM clientes
UNION ALL        -- com duplicatas, mais rápido
SELECT email FROM fornecedores;
```

## Exemplo
```sql
SELECT 'venda' AS tipo, valor FROM vendas
UNION ALL
SELECT 'estorno', -valor FROM estornos;
```

## Gotchas
- As consultas precisam ter o mesmo número de colunas e tipos compatíveis; os nomes vêm da primeira.
- `UNION` faz uma deduplicação (sort ou hash) que custa caro. Se as duplicatas forem impossíveis ou desejadas, use `UNION ALL`.
- O `ORDER BY` vale para o resultado combinado e fica no final.

## Links
[[20260201000031-cte-with-sql]]
