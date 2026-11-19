---
id: 20260201000066
title: "Pipes e redirecionamento no shell"
type: syntax
tags: [linux, shell, bash, redirecionamento]
area: programacao
created: 01/02/26
source: agent
related: [20260201000064, 20260201000077]
---

## O que é
Todo processo tem três canais padrão: entrada (stdin, descritor 0), saída (stdout, 1) e saída de erro (stderr, 2). O redirecionamento liga esses canais a arquivos; o pipe `|` liga a saída de um comando à entrada do próximo.

## Sintaxe
```bash
cmd > arquivo        # stdout para arquivo (sobrescreve)
cmd >> arquivo       # stdout para arquivo (acrescenta)
cmd 2> erros.txt     # stderr para arquivo
cmd > saida.txt 2>&1 # stdout e stderr no mesmo arquivo
cmd &> tudo.txt      # atalho do bash para o mesmo
cmd < entrada.txt    # stdin a partir de arquivo
cmd1 | cmd2          # stdout de cmd1 vira stdin de cmd2
cmd1 |& cmd2         # stdout e stderr pelo pipe (bash)
cmd > /dev/null 2>&1 # descarta toda a saída
```

## Exemplo
```bash
# contar os IPs que mais acessaram
cut -d' ' -f1 access.log | sort | uniq -c | sort -rn | head

# ver na tela e salvar ao mesmo tempo
./build.sh 2>&1 | tee build.log

# texto de várias linhas como entrada (here-doc)
cat <<EOF > config.ini
[app]
debug = false
EOF
```

`2>&1` significa "faça o descritor 2 apontar para onde o 1 aponta **agora**". Por isso a ordem importa:
- `cmd > arq 2>&1` — primeiro stdout vai para o arquivo, depois stderr copia esse destino: os dois vão para o arquivo.
- `cmd 2>&1 > arq` — stderr copia o destino atual do stdout (o terminal) e só depois stdout é redirecionado: os erros continuam aparecendo na tela.

## Gotchas
- `sort arq > arq` apaga o arquivo antes de ler, porque o shell abre (e trunca) o destino antes de rodar o comando. Use um arquivo temporário ou `sponge` do pacote moreutils.
- O pipe só passa stdout. Mensagens de erro de `cmd1` não chegam ao `grep` de `cmd1 | grep` a menos que você use `2>&1` ou `|&`.
- O código de saída de um pipeline é o do **último** comando. Em scripts, `set -o pipefail` faz o pipeline falhar se qualquer etapa falhar.

## Links
[[20260201000064-grep]]
[[20260201000077-sed-substituir-texto]]
