---
id: 20260201000024
title: "GROUP BY e funções de agregação"
type: syntax
tags: [sql, group-by, agregacao]
area: programacao
created: 01/02/26
source: agent
related: [20260201000023, 20260201000038, 20260201000040]
---

## O que é
`GROUP BY` junta as linhas que têm o mesmo valor nas colunas indicadas e permite calcular um resumo por grupo com funções de agregação: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`. O resultado tem **uma linha por grupo**.

## Sintaxe
```sql
SELECT coluna_grupo, COUNT(*), SUM(valor), AVG(valor)
FROM tabela
GROUP BY coluna_grupo;
```

## Exemplo
```sql
-- faturamento por mês e categoria
SELECT
    date_trunc('month', p.criado_em) AS mes,
    c.nome AS categoria,
    COUNT(*)          AS pedidos,
    SUM(p.valor)      AS total,
    ROUND(AVG(p.valor), 2) AS ticket_medio
FROM pedidos p
JOIN categorias c ON c.id = p.categoria_id
GROUP BY 1, 2
ORDER BY mes, total DESC;
```

`GROUP BY 1, 2` agrupa pela primeira e segunda colunas do `SELECT`. É aceito por PostgreSQL, MySQL e SQLite, mas nomear as colunas deixa a consulta mais legível. `date_trunc` é do PostgreSQL; outros bancos têm funções equivalentes.

Diferenças entre os tipos de `COUNT`:
- `COUNT(*)` conta linhas, inclusive as que têm `NULL`.
- `COUNT(coluna)` conta apenas linhas em que a coluna **não** é `NULL`.
- `COUNT(DISTINCT coluna)` conta valores distintos não nulos.

`SUM`, `AVG`, `MIN` e `MAX` também ignoram `NULL`. Um `AVG` sobre uma coluna com nulos divide pela quantidade de valores não nulos, não pelo total de linhas. Se a tabela estiver vazia, `COUNT` retorna 0 e as outras retornam `NULL`.

## Gotchas
- Toda coluna no `SELECT` que não está dentro de uma agregação precisa aparecer no `GROUP BY`. O PostgreSQL acusa erro; o MySQL antigo (sem `ONLY_FULL_GROUP_BY`) devolvia um valor arbitrário.
- Filtro sobre o resultado agregado vai no `HAVING`, não no `WHERE`.
- `NULL` forma um grupo próprio no `GROUP BY`.

## Links
[[20260201000023-having-sql]]
[[20260201000038-erro-column-must-appear-group-by]]
[[20260201000040-ordem-logica-execucao-select-sql]]
