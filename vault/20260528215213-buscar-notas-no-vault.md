---
id: 20260528215213
title: "Como buscar notas no vault"
type: command
tags: [vault, busca, obsidian, rag, grep, embed]
area: misc
created: 28/05/26
source: agent
related: []
---

## O que faz
Formas de encontrar notas no vault — por semântica, texto literal ou nome de arquivo.

## Uso

### 1. Busca semântica (RAG)
```bash
python3 embed.py search "sua pergunta aqui"
```
Retorna as notas mais próximas semanticamente. Scores ≥ 0.4 costumam ser relevantes.

### 2. Busca por texto com grep
```bash
grep -r "palavra" vault/
```

### 3. Dentro do Obsidian
| Atalho | O que faz |
|---|---|
| `Ctrl+Shift+F` | Busca texto em todo o vault |
| `Ctrl+O` | Abre nota pelo nome (fuzzy) |
| `Ctrl+G` | Abre o grafo de conexões |

## Quando usar cada um
- `embed.py search` — lembra vagamente do assunto, não sabe o termo exato
- `Ctrl+Shift+F` / `grep` — sabe a palavra-chave exata
- `Ctrl+O` — sabe o título da nota

## Links
