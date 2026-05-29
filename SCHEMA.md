# Schema — Personal Knowledge Base

Referência para estrutura de notas. O agente lê este arquivo antes de criar qualquer nota.

---

## Tipos disponíveis

| Tipo | Uso |
|------|-----|
| `syntax` | Sintaxe de linguagem — Python, SQL, regex, etc |
| `concept` | Teoria, explicação de conceito |
| `command` | Comandos de terminal, CLI, ferramentas |
| `error` | Bug, debug, solução de problema |
| `fact` | Fato, curiosidade, dado factual (qualquer área) |
| `note` | Livre — reflexão ou algo que não se encaixa nos outros tipos |

> Para adicionar um novo tipo: insira uma linha nesta tabela e crie o template correspondente abaixo.

---

## Frontmatter padrão

```yaml
---
id: 20260528143201
title: "Título da nota"
type: syntax
tags: [tag-um, tag-dois]
area: programacao
created: 28/05/26
source: agent
related: []
---
```

> `related`: lista de IDs (timestamps) das notas relacionadas — usado pelo RAG para navegação semântica.
> Os wiki-links no body da nota (`## Links`) servem ao grafo do Obsidian.

### Valores válidos para `area`

- `programacao`
- `ciencia-da-computacao`
- `cotidiano`
- `filosofia`
- `misc`

---

## Templates por tipo

### syntax

```markdown
## O que é
Descrição curta do que é essa sintaxe e pra que serve.

## Sintaxe
\```linguagem
código aqui
\```

## Exemplo
\```linguagem
exemplo prático
\```

## Gotchas
Armadilhas, edge cases, erros comuns.

## Links
[[nome-do-arquivo-relacionado]]
```

---

### concept

```markdown
## Definição
O que é, de forma direta.

## Como funciona
Explicação do mecanismo.

## Analogia
Uma comparação que facilita o entendimento (se aplicável).

## Links
[[nome-do-arquivo-relacionado]]
```

---

### command

```markdown
## O que faz
Descrição do comando.

## Uso
\```bash
comando --flags
\```

## Flags úteis
Lista das flags mais usadas e o que fazem.

## Exemplo
\```bash
exemplo real
\```

## Links
[[nome-do-arquivo-relacionado]]
```

---

### error

```markdown
## Erro
Mensagem ou descrição do erro.

## Causa
Por que acontece.

## Solução
\```linguagem
como resolver
\```

## Contexto
Em que situação esse erro aparece.

## Links
[[nome-do-arquivo-relacionado]]
```

---

### fact

```markdown
## Resposta
A resposta direta para a pergunta ou curiosidade.

## Contexto
Informação adicional relevante.

## Fonte
Fonte ou referência (se houver).

## Links
[[nome-do-arquivo-relacionado]]
```

---

### note

```markdown
## Título
Título ou tema central desta nota.

## Conteúdo
Texto livre.

## Links
[[nome-do-arquivo-relacionado]]
```

---

## Convenção de nome de arquivo

```
YYYYMMDDHHMMSS-titulo-slugificado.md
```

Exemplo: `20260528143201-window-functions-sql.md`
