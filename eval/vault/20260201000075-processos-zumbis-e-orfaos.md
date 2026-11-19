---
id: 20260201000075
title: "Processos zumbis e órfãos"
type: concept
tags: [linux, processos, sinais]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000067]
---

## Definição
**Zumbi** é um processo que já terminou, mas cuja entrada ainda está na tabela de processos porque o pai não leu seu código de saída com `wait()`. **Órfão** é um processo ainda em execução cujo pai morreu.

## Como funciona
Zumbis aparecem com estado `Z` (`<defunct>`) no `ps`. Eles não usam CPU nem memória, só uma entrada na tabela. `kill -9` não adianta, porque o processo já morreu; quem precisa agir é o pai. Encerrar o pai faz o zumbi ser adotado e recolhido.

Órfãos são adotados pelo PID 1 (o init, normalmente o systemd) ou por um processo marcado como "subreaper", que passa a fazer o `wait()` por eles.

```bash
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'
```

## Analogia
O zumbi é um funcionário que já foi embora, mas cujo crachá fica ativo até o chefe assinar a baixa.

## Links
[[20260201000067-ps-kill-sinais]]
