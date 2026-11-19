---
id: 20260201000029
title: "EXPLAIN e plano de execução"
type: command
tags: [sql, explain, performance, postgresql]
area: programacao
created: 01/02/26
source: agent
related: [20260201000028]
---

## O que faz
`EXPLAIN` mostra o **plano de execução** que o otimizador escolheu para uma consulta: quais tabelas serão lidas, em que ordem, se usará índice ou varredura completa, qual algoritmo de join e quantas linhas ele estima em cada etapa. É a principal ferramenta para entender por que uma consulta está lenta.

## Uso
```sql
EXPLAIN SELECT * FROM pedidos WHERE cliente_id = 42;
EXPLAIN ANALYZE SELECT * FROM pedidos WHERE cliente_id = 42;   -- PostgreSQL
EXPLAIN QUERY PLAN SELECT ...;                                  -- SQLite
```

## Flags úteis
- `ANALYZE` — executa a consulta de verdade e mostra tempos e contagens reais ao lado das estimativas.
- `BUFFERS` (PostgreSQL) — mostra quantas páginas vieram do cache e quantas do disco.
- `FORMAT JSON` — saída estruturada, boa para ferramentas de visualização.
- `VERBOSE` — inclui colunas de saída e nomes qualificados.

## Exemplo
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.nome, COUNT(*)
FROM pedidos p JOIN clientes c ON c.id = p.cliente_id
WHERE p.criado_em >= '2026-01-01'
GROUP BY c.nome;
```

O que procurar na saída do PostgreSQL:
- `Seq Scan` em tabela grande com filtro seletivo: provável falta de índice.
- `Index Scan` / `Index Only Scan` / `Bitmap Heap Scan`: o índice está sendo usado.
- Diferença grande entre `rows=` estimado e `actual rows=`: estatísticas desatualizadas; rode `ANALYZE nome_tabela`.
- `Nested Loop` com muitas iterações sobre um lado grande, `Hash Join`, `Merge Join`: os três algoritmos de join e quando cada um aparece.
- `Sort` com `external merge Disk`: a ordenação não coube em `work_mem`.

No MySQL, `EXPLAIN` mostra uma tabela com colunas como `type` (`ALL` significa full scan), `key` (índice usado) e `rows`; a partir do 8.0.18 também existe `EXPLAIN ANALYZE`.

Cuidado: `EXPLAIN ANALYZE` **executa** a instrução. Num `UPDATE` ou `DELETE`, os dados são alterados de fato. Para testar com segurança, envolva em transação:

```sql
BEGIN;
EXPLAIN ANALYZE DELETE FROM logs WHERE criado_em < '2025-01-01';
ROLLBACK;
```

## Links
[[20260201000028-indices-banco-de-dados]]
