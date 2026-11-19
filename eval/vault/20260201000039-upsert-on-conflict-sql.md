---
id: 20260201000039
title: "Upsert com INSERT ... ON CONFLICT"
type: syntax
tags: [sql, upsert, insert, postgresql]
area: programacao
created: 01/02/26
source: agent
related: [20260201000034]
---

## O que é
Upsert insere uma linha ou, se ela já existir (conflito de chave única), atualiza a existente, numa única instrução atômica.

## Sintaxe
```sql
-- PostgreSQL 9.5+ e SQLite 3.24+
INSERT INTO estoque (produto_id, qtd) VALUES (10, 5)
ON CONFLICT (produto_id)
DO UPDATE SET qtd = estoque.qtd + EXCLUDED.qtd;

-- ignorar se já existir
INSERT INTO tags (nome) VALUES ('sql') ON CONFLICT DO NOTHING;
```

## Exemplo
```sql
-- MySQL
INSERT INTO estoque (produto_id, qtd) VALUES (10, 5)
ON DUPLICATE KEY UPDATE qtd = qtd + VALUES(qtd);
```

## Gotchas
- `ON CONFLICT (coluna)` exige um índice único ou restrição `UNIQUE` nessa coluna.
- `EXCLUDED` é a linha que seria inserida.
- No MySQL 8.0.20+, `VALUES()` nesse contexto está obsoleto; prefira um alias de linha (`AS novo ... qtd + novo.qtd`).

## Links
[[20260201000034-delete-truncate-drop-sql]]
