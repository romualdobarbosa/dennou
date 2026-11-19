---
id: 20260201000027
title: "Window functions (funções de janela) em SQL"
type: syntax
tags: [sql, window-function, analytics]
area: programacao
created: 01/02/26
source: agent
related: [20260201000024, 20260201000031]
---

## O que é
Window functions calculam um valor para cada linha usando um conjunto de linhas relacionadas (a "janela"), **sem** colapsar o resultado como o `GROUP BY` faz. Cada linha continua no resultado e ganha uma coluna extra calculada. São suportadas por PostgreSQL, MySQL 8+, SQLite 3.25+, SQL Server e outros.

## Sintaxe
```sql
funcao() OVER (
    PARTITION BY coluna_grupo
    ORDER BY coluna_ordem
    ROWS BETWEEN ... AND ...
)
```

- `PARTITION BY` divide as linhas em grupos independentes (opcional; sem ele, a janela é a tabela inteira).
- `ORDER BY` define a ordem dentro de cada partição.
- A cláusula de frame (`ROWS`/`RANGE`/`GROUPS`) define quais linhas, relativas à atual, entram no cálculo.

## Exemplo
Numerar os pedidos de cada cliente, do mais recente para o mais antigo:

```sql
SELECT
    cliente_id,
    id AS pedido_id,
    criado_em,
    ROW_NUMBER() OVER (PARTITION BY cliente_id ORDER BY criado_em DESC) AS n
FROM pedidos;
```

Funções de ranking:
- `ROW_NUMBER()` — numeração sequencial sem empates (1, 2, 3, 4).
- `RANK()` — empates recebem o mesmo número e o próximo pula (1, 2, 2, 4).
- `DENSE_RANK()` — empates recebem o mesmo número sem pular (1, 2, 2, 3).
- `NTILE(n)` — divide a partição em n faixas aproximadamente iguais.

Funções de deslocamento:
- `LAG(coluna, n)` — valor de n linhas antes; útil para variação em relação ao período anterior.
- `LEAD(coluna, n)` — valor de n linhas depois.
- `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE` — valores em posições do frame.

Agregações como janela (total acumulado e média móvel):

```sql
SELECT
    dia,
    vendas,
    SUM(vendas) OVER (ORDER BY dia) AS acumulado,
    AVG(vendas) OVER (ORDER BY dia ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS media_7d,
    vendas - LAG(vendas) OVER (ORDER BY dia) AS variacao
FROM vendas_diarias;
```

Pegar o último pedido de cada cliente (top-N por grupo). Window functions não podem ser usadas no `WHERE`, porque são calculadas depois dele; por isso se usa uma subquery ou CTE:

```sql
WITH ordenados AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY cliente_id ORDER BY criado_em DESC) AS n
    FROM pedidos
)
SELECT * FROM ordenados WHERE n = 1;
```

Alguns bancos (Snowflake, BigQuery, DuckDB) têm a cláusula `QUALIFY`, que filtra pelo resultado da window function sem subquery. Ela não faz parte do PostgreSQL nem do MySQL.

Percentual de cada linha em relação ao total do grupo, sem precisar de subquery para calcular o total:

```sql
SELECT
    categoria,
    produto,
    vendas,
    ROUND(100.0 * vendas / SUM(vendas) OVER (PARTITION BY categoria), 1) AS pct_categoria
FROM vendas_por_produto;
```

Aqui a janela não tem `ORDER BY`, então a soma considera a partição inteira. Esse detalhe, ter ou não ter `ORDER BY` dentro do `OVER`, muda o resultado das agregações, como explicado no fim desta nota.

A mesma janela pode ser nomeada e reaproveitada com `WINDOW`:

```sql
SELECT dia, SUM(vendas) OVER w, AVG(vendas) OVER w
FROM vendas_diarias
WINDOW w AS (ORDER BY dia);
```

## Gotchas
### O frame padrão e o LAST_VALUE "quebrado"
Quando a janela tem `ORDER BY` mas nenhum frame explícito, o padrão do SQL é `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`: o frame vai do início da partição **até a linha atual** (incluindo as linhas empatadas com ela). Por isso `LAST_VALUE(x) OVER (ORDER BY y)` devolve o valor da própria linha atual, e não o último da partição. A correção é declarar o frame inteiro:

```sql
LAST_VALUE(preco) OVER (
    PARTITION BY produto_id
    ORDER BY data
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
) AS ultimo_preco
```

Alternativa comum: usar `FIRST_VALUE` com a ordem invertida (`ORDER BY data DESC`), que funciona com o frame padrão.

### RANGE vs ROWS com empates
Pelo mesmo motivo, um total acumulado `SUM(x) OVER (ORDER BY dia)` trata linhas com o mesmo `dia` como pares: todas recebem o mesmo acumulado, que já inclui todas elas. Se você quer que o acumulado avance linha a linha, use `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` e um critério de desempate no `ORDER BY`. Sem `ORDER BY` nenhum, o frame é a partição inteira.

## Links
[[20260201000024-group-by-agregacao-sql]]
[[20260201000031-cte-with-sql]]
