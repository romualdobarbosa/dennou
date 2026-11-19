---
id: 20260201000028
title: "Índices em banco de dados"
type: concept
tags: [sql, indice, performance]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000029, 20260201000032]
---

## Definição
Índice é uma estrutura auxiliar que o banco mantém ao lado da tabela para encontrar linhas sem precisar ler a tabela inteira (full scan). O tipo mais comum é a **B-tree**, uma árvore balanceada e ordenada.

## Como funciona
```sql
CREATE INDEX idx_pedidos_cliente ON pedidos (cliente_id);
CREATE UNIQUE INDEX idx_usuarios_email ON usuarios (email);
CREATE INDEX idx_pedidos_cli_data ON pedidos (cliente_id, criado_em);
```

Com o índice, uma busca como `WHERE cliente_id = 42` desce a árvore em O(log n) e vai direto às linhas certas. Como a B-tree é ordenada, ela também acelera intervalos (`BETWEEN`, `>`, `<`), `ORDER BY` na mesma ordem do índice e `LIKE 'abc%'` com prefixo fixo.

**Índice composto e regra do prefixo à esquerda:** um índice em `(cliente_id, criado_em)` serve para filtros em `cliente_id` sozinho ou em `cliente_id` + `criado_em`, mas em geral não para `criado_em` sozinho. A ordem das colunas importa.

**Quando o índice não é usado:**
- Função aplicada à coluna: `WHERE lower(email) = 'x'` não usa um índice em `email` (a menos que exista um índice de expressão em `lower(email)`).
- `LIKE '%abc'` com curinga no início.
- Consultas que retornam grande parte da tabela; aí o full scan costuma ser mais barato, e o otimizador escolhe isso.
- Tipos diferentes na comparação, que forçam conversão implícita.

**Custo:** cada índice ocupa disco e precisa ser atualizado em todo `INSERT`, `UPDATE` e `DELETE`. Índices demais deixam a escrita lenta. Chaves primárias e restrições `UNIQUE` já criam índice automaticamente na maioria dos bancos; chaves estrangeiras, no PostgreSQL, **não**.

Para confirmar se um índice está sendo usado, olhe o plano de execução com `EXPLAIN`.

## Analogia
É o índice remissivo de um livro: em vez de folhear página por página procurando "recursão", você vai ao fim do livro, acha a palavra em ordem alfabética e pula direto para as páginas certas.

## Links
[[20260201000029-explain-plano-execucao-sql]]
[[20260201000032-subquery-exists-in-join-sql]]
