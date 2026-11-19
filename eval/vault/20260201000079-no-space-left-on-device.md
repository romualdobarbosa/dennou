---
id: 20260201000079
title: "Erro: No space left on device com espaço sobrando"
type: error
tags: [linux, disco, inode, armazenamento]
area: programacao
created: 01/02/26
source: agent
related: [20260201000074, 20260201000078]
---

## Erro
```
No space left on device
```
...mas `df -h` mostra gigas livres.

## Causa
Duas causas comuns:
1. **Inodes esgotados**: cada arquivo usa um inode, e milhões de arquivos minúsculos (cache, sessões, filas de e-mail) esgotam os inodes antes do espaço.
2. **Arquivo apagado ainda aberto**: um processo mantém aberto um log apagado; o espaço só volta quando o processo fecha o arquivo.

## Solução
```bash
df -i                       # uso de inodes por sistema de arquivos
lsof +L1                    # arquivos apagados ainda abertos
sudo systemctl restart nome-do-servico   # libera o arquivo aberto
```

## Contexto
Em ext4, cerca de 5% dos blocos ficam reservados para o root por padrão, então um usuário comum pode receber o erro enquanto o `df` ainda mostra um pouco de espaço livre.

## Links
[[20260201000074-df-du-espaco-em-disco]]
[[20260201000078-hard-link-vs-link-simbolico]]
