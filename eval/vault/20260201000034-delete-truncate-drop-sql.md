---
id: 20260201000034
title: "Diferença entre DELETE, TRUNCATE e DROP"
type: fact
tags: [sql, ddl, dml]
area: programacao
created: 01/02/26
source: agent
related: [20260201000033]
---

## Resposta
- `DELETE FROM t WHERE ...` remove **linhas** (todas, se não tiver `WHERE`). É DML, linha a linha, dispara triggers e pode ser desfeito com `ROLLBACK`.
- `TRUNCATE TABLE t` remove **todas as linhas** de uma vez, mantendo a estrutura. Muito mais rápido; não aceita `WHERE`.
- `DROP TABLE t` remove a **tabela inteira**: dados, estrutura, índices e permissões.

## Contexto
`TRUNCATE` normalmente reinicia contadores de auto-incremento (no PostgreSQL só com `RESTART IDENTITY`). No PostgreSQL ele é transacional; no MySQL causa commit implícito e não pode ser desfeito. Tabelas referenciadas por chave estrangeira exigem `TRUNCATE ... CASCADE` no PostgreSQL.

## Fonte
Documentação do PostgreSQL e do MySQL.

## Links
[[20260201000033-transacoes-acid-sql]]
