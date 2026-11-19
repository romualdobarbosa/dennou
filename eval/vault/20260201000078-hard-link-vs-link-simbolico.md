---
id: 20260201000078
title: "Hard link vs link simbólico"
type: concept
tags: [linux, link, sistema-de-arquivos]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000079]
---

## Definição
Um **hard link** é outro nome para o mesmo inode: os dois nomes apontam para os mesmos dados no disco, e nenhum é "o original". Um **link simbólico** (symlink) é um arquivo pequeno que contém o **caminho** de outro arquivo.

## Como funciona
```bash
ln dados.txt copia-hard.txt        # hard link
ln -s /opt/app/v2 /opt/app/atual   # link simbólico
ls -li                             # mostra o número do inode
readlink -f atual                  # caminho final de um symlink
```

- Hard link: os dados só são liberados quando o último nome é apagado. Não pode apontar para diretórios nem atravessar sistemas de arquivos diferentes.
- Symlink: funciona com diretórios e entre partições, mas quebra se o alvo for movido ou apagado. Caminhos relativos no symlink são resolvidos a partir da pasta do link.

## Analogia
Hard link é a mesma pessoa com dois nomes no registro civil; symlink é um bilhete dizendo "procure fulano no endereço tal".

## Links
[[20260201000079-no-space-left-on-device]]
