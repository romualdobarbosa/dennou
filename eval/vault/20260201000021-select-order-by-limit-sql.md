---
id: 20260201000021
title: "SELECT com ORDER BY e LIMIT"
type: syntax
tags: [sql, select, ordenacao]
area: programacao
created: 01/02/26
source: agent
related: [20260201000022, 20260201000040]
---

## O que é
Estrutura básica de consulta: escolhe colunas (`SELECT`), a tabela (`FROM`), a ordem do resultado (`ORDER BY`) e quantas linhas devolver (`LIMIT`).

## Sintaxe
```sql
SELECT coluna1, coluna2
FROM tabela
ORDER BY coluna1 DESC, coluna2 ASC
LIMIT 10 OFFSET 20;
```

## Exemplo
```sql
-- 5 produtos mais caros
SELECT nome, preco
FROM produtos
ORDER BY preco DESC
LIMIT 5;
```

## Gotchas
- Sem `ORDER BY`, a ordem das linhas não é garantida, mesmo que pareça estável.
- `LIMIT` é de PostgreSQL, MySQL e SQLite; SQL Server usa `TOP`, e o padrão SQL é `FETCH FIRST n ROWS ONLY`.
- Paginação com `OFFSET` alto fica lenta, porque o banco precisa ler e descartar as linhas puladas.

## Links
[[20260201000022-where-sql]]
[[20260201000040-ordem-logica-execucao-select-sql]]
