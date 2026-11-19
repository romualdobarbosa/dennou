---
id: 20260201000077
title: "sed: substituir e editar texto em fluxo"
type: command
tags: [linux, sed, texto, regex]
area: programacao
created: 01/02/26
source: agent
related: [20260201000064, 20260201000066]
---

## O que faz
Editor de fluxo: lê texto linha a linha, aplica comandos (substituir, apagar, imprimir) e escreve o resultado. O uso mais comum é substituir texto em arquivos sem abrir um editor.

## Uso
```bash
sed 's/antigo/novo/' arquivo      # primeira ocorrência de cada linha
sed 's/antigo/novo/g' arquivo     # todas as ocorrências
sed -i 's/antigo/novo/g' arquivo  # altera o próprio arquivo
```

## Flags úteis
- `-i` — edição no lugar; `-i.bak` guarda uma cópia de segurança.
- `-E` — regex estendida.
- `-n` com `p` — imprime só as linhas selecionadas: `sed -n '10,20p' arq`.
- `/padrão/d` — apaga linhas que casam.

## Exemplo
```bash
sed -i 's|/usr/local|/opt|g' config.ini   # outro delimitador evita escapar as barras
sed -i '/^#/d' lista.txt                  # remove linhas de comentário
```

No macOS (sed BSD), `-i` exige um argumento: `sed -i '' 's/a/b/' arq`.

## Links
[[20260201000064-grep]]
[[20260201000066-pipes-e-redirecionamento-shell]]
