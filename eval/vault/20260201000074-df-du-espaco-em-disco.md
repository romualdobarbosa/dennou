---
id: 20260201000074
title: "df e du: espaço em disco"
type: command
tags: [linux, disco, armazenamento]
area: programacao
created: 01/02/26
source: agent
related: [20260201000079, 20260201000073]
---

## O que faz
`df` mostra o espaço usado e livre de cada **sistema de arquivos** montado. `du` mostra quanto espaço **arquivos e diretórios** ocupam.

## Uso
```bash
df -h                   # tamanhos legíveis (G, M)
du -sh pasta/           # total de uma pasta
```

## Flags úteis
- `df -h` — unidades legíveis; `df -T` — mostra o tipo do sistema de arquivos.
- `du -s` — só o total; `-h` — legível.
- `du -h --max-depth=1` (ou `-d 1`) — total de cada subpasta.

## Exemplo
```bash
# o que está ocupando espaço no diretório atual, do maior para o menor
du -h -d 1 . | sort -rh | head
```

Para explorar interativamente, a ferramenta `ncdu` mostra a árvore ordenada por tamanho.

## Links
[[20260201000079-no-space-left-on-device]]
[[20260201000073-tar-compactacao]]
