---
id: 20260201000071
title: "Erro: command not found e a variável PATH"
type: error
tags: [linux, shell, path]
area: programacao
created: 01/02/26
source: agent
related: [20260201000072]
---

## Erro
```
bash: meuapp: command not found
```

## Causa
O shell procura comandos apenas nos diretórios listados em `PATH`, na ordem. Se o executável está em outro lugar (por exemplo `~/.local/bin`, onde o `pip install --user` coloca scripts), só funciona com o caminho completo.

## Solução
```bash
echo $PATH                          # diretórios pesquisados
which meuapp; type meuapp           # onde o shell acha (ou não) o comando
export PATH="$HOME/.local/bin:$PATH"   # na sessão atual
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # permanente
hash -r                             # limpa o cache de caminhos do bash
```

## Contexto
Também ocorre quando o pacote não está instalado, quando o arquivo não tem permissão de execução (aí o erro costuma ser "Permission denied") e com scripts no diretório atual, que precisam de `./script.sh` porque `.` não está no PATH.

## Links
[[20260201000072-variaveis-de-ambiente-export]]
