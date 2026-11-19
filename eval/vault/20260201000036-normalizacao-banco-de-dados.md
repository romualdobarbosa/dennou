---
id: 20260201000036
title: "Normalização de banco de dados: 1FN, 2FN, 3FN e FNBC"
type: concept
tags: [sql, normalizacao, modelagem]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000028, 20260201000033]
---

## Definição
Normalização é o processo de organizar tabelas para reduzir redundância e evitar anomalias de inserção, atualização e exclusão. Ela é feita em etapas chamadas **formas normais**, cada uma com uma regra a mais que a anterior. Na prática, a maioria dos sistemas mira a terceira forma normal (3FN).

## Como funciona
O conceito central é a **dependência funcional**: `A → B` significa que, conhecendo o valor de A, o valor de B fica determinado. Por exemplo, `cpf → nome`.

### Problema de partida
Imagine uma planilha de pedidos com as colunas: `pedido_id, data, cliente_nome, cliente_cidade, produtos` (com vários produtos separados por vírgula na mesma célula). Se o cliente muda de cidade, é preciso atualizar dezenas de linhas (anomalia de atualização). Não dá para cadastrar um cliente sem pedido (anomalia de inserção). Apagar o último pedido de alguém apaga o próprio cliente (anomalia de exclusão).

### Primeira forma normal (1FN)
Cada coluna guarda um valor **atômico**, e não há grupos repetidos. A coluna `produtos` com "caneta, caderno" viola a 1FN. A solução é uma linha por item, numa tabela `itens_pedido (pedido_id, produto_id, quantidade)`.

### Segunda forma normal (2FN)
Está na 1FN e nenhum atributo não-chave depende de **parte** de uma chave composta. Em `itens_pedido` com chave `(pedido_id, produto_id)`, uma coluna `produto_nome` depende só de `produto_id`: é uma dependência parcial. Move-se `produto_nome` para a tabela `produtos`. Tabelas com chave primária de uma coluna só já estão automaticamente na 2FN se estiverem na 1FN.

### Terceira forma normal (3FN)
Está na 2FN e nenhum atributo não-chave depende de **outro atributo não-chave** (sem dependências transitivas). Em `pedidos (pedido_id, cliente_id, cliente_cidade)`, temos `pedido_id → cliente_id → cliente_cidade`. A cidade depende do cliente, não do pedido, então vai para a tabela `clientes`.

Um resumo popular da 3FN: todo atributo não-chave deve depender "da chave, da chave inteira e de nada além da chave".

### Desnormalização
Normalizar demais pode exigir muitos joins em consultas de leitura intensa. Em data warehouses, relatórios e caches, é comum desnormalizar de propósito (modelo estrela, colunas calculadas, tabelas de resumo), aceitando redundância em troca de leitura rápida. A decisão deve ser consciente e acompanhada de um jeito de manter os dados redundantes sincronizados.

### Forma normal de Boyce-Codd (FNBC)
A FNBC (BCNF, em inglês) é uma versão mais rígida da 3FN. A regra é: para **toda** dependência funcional não trivial `X → Y`, X precisa ser uma superchave. A 3FN aceita uma exceção que a FNBC não aceita: na 3FN, `X → Y` é tolerada quando Y é um atributo **primo**, ou seja, faz parte de alguma chave candidata.

Exemplo clássico: a tabela `matriculas (aluno, disciplina, professor)`, em que cada professor ensina uma única disciplina (`professor → disciplina`) e cada aluno tem um professor por disciplina. As chaves candidatas são `(aluno, disciplina)` e `(aluno, professor)`. A dependência `professor → disciplina` tem um determinante (`professor`) que não é superchave, mas `disciplina` é atributo primo, então a tabela está na 3FN e **não** está na FNBC. A anomalia: se o professor trocar de disciplina, é preciso atualizar várias linhas. A decomposição em FNBC separa `professores (professor, disciplina)` e `matriculas (aluno, professor)`.

O preço: a decomposição para FNBC nem sempre preserva todas as dependências funcionais. Aqui, a regra "um aluno tem um só professor por disciplina" deixa de poder ser garantida por uma restrição simples numa única tabela. Por isso a 3FN continua sendo o alvo usual. Acima da FNBC ainda existem a 4FN, que trata dependências multivaloradas, e a 5FN, que trata dependências de junção, raramente aplicadas no dia a dia.

## Analogia
É como arrumar uma cozinha: cada coisa num lugar só. Se o sal fica em três armários, um dia você reabastece um e esquece os outros.

## Links
[[20260201000028-indices-banco-de-dados]]
[[20260201000033-transacoes-acid-sql]]
