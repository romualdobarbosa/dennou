---
id: 20260528220019
title: "Colorir nós no Graph View do Obsidian"
type: command
tags: [obsidian, graph-view, grafo, cor, grupos, tags]
area: misc
created: 28/05/26
source: agent
related: [20260528215639]
---

## O que faz
Permite colorir nós do grafo por grupos definidos com filtros — por tag, pasta ou nome de arquivo.

## Uso
No painel do Graph View: **Groups → New group**

Cada grupo tem uma cor e um filtro que define quais nós pertencem a ele.

## Filtros disponíveis
| Filtro | O que seleciona |
|---|---|
| `tag:#sql` | Notas com a tag `sql` no frontmatter |
| `path:vault/` | Notas dentro de uma pasta |
| `file:nome` | Notas com esse nome |

## Exemplo
| Grupo | Filtro | Cor sugerida |
|---|---|---|
| SQL | `tag:#sql` | azul |
| Obsidian | `tag:#obsidian` | roxo |

## Gotchas
- As tags dos filtros são as mesmas do frontmatter (`tags: [sql, obsidian, ...]`)
- Quanto mais consistente o tagging das notas, mais útil fica o grafo colorido

## Links
[[20260528215639-graph-view-obsidian]]
