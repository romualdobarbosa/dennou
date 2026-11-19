---
id: 20260201000033
title: "Transações e propriedades ACID"
type: concept
tags: [sql, transacao, acid, concorrencia]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000034]
---

## Definição
Uma transação é um conjunto de operações tratado pelo banco como uma unidade indivisível: ou todas são aplicadas, ou nenhuma é. As garantias que um banco relacional oferece às transações são resumidas pela sigla **ACID**.

## Como funciona
```sql
BEGIN;
UPDATE contas SET saldo = saldo - 100 WHERE id = 1;
UPDATE contas SET saldo = saldo + 100 WHERE id = 2;
COMMIT;      -- confirma as duas
-- ou ROLLBACK; para desfazer as duas
```

### As quatro propriedades
- **Atomicidade** — tudo ou nada. Se a segunda atualização falhar, a primeira é desfeita. Uma queda de energia no meio da transferência não deixa dinheiro "sumir".
- **Consistência** — a transação leva o banco de um estado válido a outro válido, respeitando restrições como `CHECK`, `UNIQUE` e chaves estrangeiras. Se alguma for violada, a transação inteira falha.
- **Isolamento** — transações concorrentes não deveriam enxergar os estados intermediários umas das outras. O grau exato de isolamento é configurável (veja abaixo).
- **Durabilidade** — depois do `COMMIT`, os dados sobrevivem a quedas. Bancos implementam isso com um log de escrita antecipada (WAL, write-ahead log): a alteração é gravada no log em disco antes de o commit ser confirmado.

### Savepoints
Dentro de uma transação, dá para marcar pontos intermediários e desfazer só parte do trabalho:

```sql
BEGIN;
INSERT INTO pedidos ...;
SAVEPOINT antes_itens;
INSERT INTO itens ...;           -- falhou
ROLLBACK TO SAVEPOINT antes_itens;
COMMIT;                          -- o pedido é mantido
```

### Autocommit
Sem um `BEGIN` explícito, a maioria dos bancos trata cada instrução como uma transação própria (modo autocommit). Bibliotecas de acesso costumam fazer o contrário: o módulo `sqlite3` do Python, por exemplo, abre transações implicitamente antes de instruções de modificação, e é preciso chamar `conn.commit()`; esquecer disso faz as alterações se perderem ao fechar a conexão.

### Concorrência e travas
Duas transações que atualizam a mesma linha não podem fazê-lo ao mesmo tempo: a segunda espera a primeira terminar. Quando duas transações esperam uma pela outra em ciclo, ocorre um **deadlock**; o banco detecta e aborta uma delas, que precisa ser repetida pela aplicação. Para ler e depois atualizar com segurança, use `SELECT ... FOR UPDATE`, que trava as linhas lidas até o fim da transação.

Transações longas são problemáticas: seguram travas, aumentam a contenção e, no PostgreSQL, impedem o `VACUUM` de limpar versões antigas de linhas.

### Níveis de isolamento e anomalias
O padrão SQL define quatro níveis de isolamento, do mais fraco ao mais forte, de acordo com as anomalias que cada um permite:

| Nível | Leitura suja | Leitura não repetível | Leitura fantasma |
|---|---|---|---|
| READ UNCOMMITTED | possível | possível | possível |
| READ COMMITTED | não | possível | possível |
| REPEATABLE READ | não | não | possível |
| SERIALIZABLE | não | não | não |

- **Leitura suja**: ler dados de outra transação que ainda não fez commit.
- **Leitura não repetível**: ler a mesma linha duas vezes na transação e obter valores diferentes.
- **Leitura fantasma**: repetir uma consulta por intervalo e aparecerem linhas novas.

Os bancos escolhem padrões diferentes:
- **PostgreSQL**: padrão `READ COMMITTED`. Pedir `READ UNCOMMITTED` resulta em comportamento de `READ COMMITTED`, e o `REPEATABLE READ` dele também impede leituras fantasmas.
- **MySQL com InnoDB**: padrão `REPEATABLE READ`.
- **SQL Server** e **Oracle**: padrão `READ COMMITTED`.
- **SQLite**: transações são serializáveis por padrão.

```sql
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;   -- logo após o BEGIN
```

No nível `SERIALIZABLE`, o banco pode abortar transações com erro de serialização (SQLSTATE `40001`), e a aplicação deve estar preparada para repetir a transação.

## Analogia
Uma transferência bancária é como uma troca de envelopes feita dentro de uma sala fechada: quem está do lado de fora vê a situação antes ou depois da troca, nunca alguém com dois envelopes na mão.

## Links
[[20260201000034-delete-truncate-drop-sql]]
